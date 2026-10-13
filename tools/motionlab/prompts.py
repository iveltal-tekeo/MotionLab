"""The prompt library (0.4): proven prompts per kind, each split into its structure, so Claude can write a new one in
a structure that already worked (`/write-prompt`).

One home: knowledge\\local\\prompts\\<kind>\\<id>.json (private to this PC; sharing your own prompts comes later).
A prompt = the text, where it came from (`tested` by you, a `creator`'s public prompt + link, or `written` by
Claude from examples), the model (shots), your rating of what it made (good / ok / bad + a note), and its structure
(ordered slots with the words that filled them; Claude writes it when the prompt is added). Used by
tools\\prompts.py, the app's Prompts page and MCP `prompts()`.
"""
from __future__ import annotations

import datetime as _dt
import re
import threading
import unicodedata
from pathlib import Path

from .util import LAB, read_json, safe_name, write_json

FOLDER = "knowledge/local/prompts"                      # relative to the lab (the app's "Folder" button)
HOME = LAB / FOLDER
KINDS = {"brief": "Brief for Claude", "shot": "Video-model shot", "image": "Image (still / start frame)",
         "hook": "Hook (first 3 s)", "script": "Talking script"}      # brief first: the user's main use (0.3.4)
# what each kind is, in words (the Add dialog and the kind chips' tooltips)
KIND_HELP = {"shot": "one shot of AI video - for Seedance, Kling, Higgsfield...",
             "image": "a still or a start frame - for Nano Banana, GPT Image, Kling Image...",
             "hook": "the first 3 seconds you say or show",
             "script": "the words you say on camera",
             "brief": "you tell Claude how to make or edit a video: length, feel, colour, pacing, SFX, graphics..."}
SOURCES = ("tested", "creator", "written")
RATINGS = ("good", "ok", "bad")
# the slots Claude splits a prompt into (a guide, not a schema: a prompt may skip some or need another). "references"
# = what each uploaded file is for, "keep" = what must not change, "change" = the transformation (lock first, then
# change - the order the guides that work use)
SLOTS = {
    "shot": ["references", "keep", "change", "subject", "action", "setting", "camera", "lens", "light", "look",
             "motion", "beats", "audio", "length / aspect", "avoid"],
    "image": ["references", "keep", "change", "subject", "setting", "composition", "light", "look", "materials",
              "avoid"],
    "hook": ["pattern", "opening line", "on screen", "promise"],
    "script": ["hook", "problem", "points", "proof", "call to action"],
    # 0.3.4: a brief = what Claude needs to make a whole video; Claude's check marks each clear / vague / missing.
    # In the order a video is made (the app groups them: the plan, the edit, sound, look & text, finish); effects,
    # voice & audio and ending added after the user asked "what other parts should Claude check?"
    "brief": ["format & length", "story & hook", "feel / style", "footage", "order & structure",
              "pacing & cuts", "transitions", "effects",
              "voice & audio", "music", "sfx",
              "colour", "motion graphics", "captions & text",
              "ending", "deliverable", "questions first"],
}
STATUSES = ("clear", "vague", "missing")                # Claude's check of one slot (structure[i].status)
HOOK_PATTERNS = ["question", "bold claim", "number", "story", "contrarian", "demo", "curiosity gap", "call-out"]
_LOCK = threading.RLock()


def _today() -> str:
    return _dt.date.today().isoformat()


def _path(pid: str) -> Path:
    m = re.fullmatch(r"(shot|image|hook|script|brief)-(\d{3,})", str(pid))
    if not m:
        raise ValueError(f"not a prompt id: {pid!r} (like shot-001, image-002, hook-003, script-004)")
    return HOME / m[1] / f"{pid}.json"


def load_all(kind: str = "") -> list[dict]:
    """Every prompt (of one kind), best examples first (see `rank`)."""
    kinds = [kind] if kind else list(KINDS)
    out = []
    for k in kinds:
        for p in sorted((HOME / k).glob(f"{k}-*.json")):
            try:
                out.append(read_json(p))
            except (OSError, ValueError):
                continue
    return sorted(out, key=rank)


def get(pid: str) -> dict:
    p = _path(pid)
    if not p.exists():
        raise ValueError(f"no prompt {pid}")
    return read_json(p)


def rank(r: dict) -> tuple:
    """Sort key - the examples Claude should copy first: what the user rated good (tested before written before
    creator), then unrated creators' prompts, ok, unrated rest, bad last; inside each group Claude's review stars
    (more first). The user's rating of a real result always outranks Claude's reading of the text."""
    rating = (r.get("result") or {}).get("rating")
    src = (r.get("source") or {}).get("type")
    order = {"good": 0, "ok": 2, "bad": 4}.get(rating, 3 if src != "creator" else 1)
    stars = (r.get("review") or {}).get("stars")
    return (order, -(stars if stars is not None else -1), {"tested": 0, "written": 1, "creator": 2}.get(src, 3),
            r.get("id", ""))


def next_id(kind: str) -> str:
    nums = [int(p.stem.split("-")[1]) for p in (HOME / kind).glob(f"{kind}-*.json") if p.stem.split("-")[1].isdigit()]
    return f"{kind}-{max(nums, default=0) + 1:03d}"


def _check(r: dict) -> None:
    if r.get("kind") not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)} (got {r.get('kind')!r})")
    if not str(r.get("text", "")).strip():
        raise ValueError("a prompt needs its text")
    s = r.get("source") or {}
    if s.get("type") not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)} (got {s.get('type')!r})")
    rating = (r.get("result") or {}).get("rating")
    if rating not in (None, *RATINGS):
        raise ValueError(f"rating must be one of {', '.join(RATINGS)} (got {rating!r})")
    for x in r.get("structure") or []:
        if not (isinstance(x, dict) and x.get("slot") and "text" in x):
            raise ValueError("structure = a list of {slot, text} (+ status: clear / vague / missing, tip)")
        if x.get("status") not in (None, *STATUSES):
            raise ValueError(f"structure status: {', '.join(STATUSES)} (got {x.get('status')!r})")
    if not isinstance(r.get("wishes") or {}, dict):
        raise ValueError("wishes = {slot: what the user wants}")
    ex = r.get("examples") or []
    if not (isinstance(ex, list)
            and all(isinstance(x, str) and x.strip(".") and not set(x) & set("/\\:") for x in ex)):
        raise ValueError("examples = file names in knowledge\\local\\prompts\\examples")
    refs = r.get("style_refs") or []
    if not (isinstance(refs, list) and len(refs) <= 5 and all(isinstance(x, str) and x and safe_name(x) == x
                                                                for x in refs)):
        raise ValueError("style_refs = up to 5 analysed references (their folder names in analysis)")
    rv = r.get("review")
    if rv is not None:
        if not (isinstance(rv, dict) and isinstance(rv.get("stars"), int) and 0 <= rv["stars"] <= 5):
            raise ValueError("review = {stars: 0-5, why, fix}")
    if r.get("step") is not None and not (isinstance(r["step"], int) and r["step"] >= 1):
        raise ValueError("step = 1, 2, ... (its place in the workflow)")


def _review(rv: dict | None) -> dict | None:
    """Claude's review of the TEXT (0-5 stars: will a model do what it asks?) - not a result; the user's own
    rating of what the model made lives in `result`."""
    if not rv:
        return None
    return {"stars": rv.get("stars"), "why": str(rv.get("why") or "").strip(), "fix": str(rv.get("fix") or "").strip(),
            "by": rv.get("by") or "claude", "date": rv.get("date") or _today()}


def add(rec: dict) -> dict:
    """Save a new prompt (gets the next id of its kind). rec: kind, text, source {type, creator?, link?, file?}, and
    optionally title, model, result {rating, note}, structure [{slot, text}], pattern, tags, made_from [ids],
    review {stars 0-5, why, fix}, workflow (name of a multi-step recipe) + step (1, 2, ...), notes (how to use it),
    style_refs (analysed references whose measured style it follows)."""
    r = {"kind": rec.get("kind"), "title": str(rec.get("title") or "").strip(), "text": str(rec.get("text") or "").strip(),
         "model": str(rec.get("model") or "").strip(), "source": dict(rec.get("source") or {}),
         "result": {"rating": None, "note": "", **(rec.get("result") or {})},
         "structure": rec.get("structure") or None, "pattern": rec.get("pattern") or "",
         "tags": list(rec.get("tags") or []), "made_from": list(rec.get("made_from") or []),
         "review": _review(rec.get("review")), "workflow": str(rec.get("workflow") or "").strip(),
         "step": rec.get("step"), "notes": str(rec.get("notes") or "").strip(),
         "style_refs": list(rec.get("style_refs") or []), "added": _today(), "updated": _today()}
    _check(r)
    with _LOCK:
        r["id"] = next_id(r["kind"])
        write_json(_path(r["id"]), {"id": r["id"], **r}, indent=1)
    return get(r["id"])


def update(pid: str, **changes) -> dict:
    """Change fields of a saved prompt: title, model, structure (Claude's check: per slot what the prompt says +
    status clear / vague / missing + a tip), pattern, tags, workflow, step, notes, review (Claude's stars), wishes
    (the user's: {slot: what I want} - read by `/write-prompt optimize`), style_refs (analysed references whose
    measured style the prompt follows), rating + note (the user's) - the text and the source stay as they were
    added."""
    with _LOCK:
        r = get(pid)
        for k in ("title", "model", "structure", "pattern", "tags", "workflow", "step", "notes", "wishes",
                  "style_refs", "examples"):
            if k in changes and changes[k] is not None:
                r[k] = changes[k]
        if changes.get("review") is not None:
            r["review"] = _review(changes["review"])
        res = r.setdefault("result", {"rating": None, "note": ""})
        if "rating" in changes:
            res["rating"] = changes["rating"] or None
        if changes.get("note") is not None:
            res["note"] = str(changes["note"]).strip()
        r["updated"] = _today()
        _check(r)
        write_json(_path(pid), r, indent=1)
    return r


def set_kind(pid: str, kind: str) -> dict:
    """A prompt saved under the wrong kind (the Add dialog guesses it) -> the right kind: a new id of that kind, the old
    file goes (ids carry the kind)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)} (got {kind!r})")
    with _LOCK:
        r = get(pid)
        if r["kind"] == kind:
            return r
        old = _path(pid)
        r.update(kind=kind, id=next_id(kind), updated=_today())
        _check(r)
        write_json(_path(r["id"]), r, indent=1)
        old.unlink()
    return r


# ------------------------------------------------------------------------------------------------ style references
# 0.3.5: "al estilo vlog de Clavero" - when a Clavero video is analysed already, its measured style (pacing, effects,
# words) goes into the prompt instead of "give a link". The user links it on the card (or Claude, on a clear match).
STYLE_KINDS = ("brief", "script", "hook")              # prompts that make a whole video / its talking (Run it)
# words in titles that name no one (they would match half the prompts)
_GENERIC = set("""vlog vlogs video videos official music edit edits short shorts reel reels tiktok youtube instagram
day days dia dias part parte episode episodio trailer teaser live full version remix lyric lyrics letra audio prod feat
with from this that what when your about como para with sobre todo toda todos cinematic cinematico travel viaje viajes
daily week semana first primer primera nuevo nueva new best mejor mejores review tutorial highlights recap part1 part2
""".split())


def _fold(s: str) -> str:
    """Lower case without accents, so "Día" finds "dia" and "CLAVERO" finds "Clavero"."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(s)) if not unicodedata.combining(c)).lower()


def _words(s: str) -> set[str]:
    return set(re.findall(r"\w+", _fold(s)))


def suggest_refs(text: str, styles: list[dict], have=()) -> list[dict]:
    """Analysed references a prompt seems to mean: the one who made it named in the prompt ("made by Clavero"),
    else a distinctive word of its title. styles = knowledge.style() of each reference. Best first, at most 4;
    the ones already linked (have) are left out."""
    words, folded = _words(text), " " + " ".join(re.findall(r"\w+", _fold(text))) + " "
    out = []
    for s in styles:
        if not s or s.get("test") or s["name"] in have:
            continue
        up = " ".join(re.findall(r"\w+", _fold(s.get("uploader") or "")))
        if up and len(up) >= 3 and f" {up} " in folded:
            out.append((0, {"name": s["name"], "why": f"made by {s['uploader']}"}))
            continue
        upw = {w for w in up.split() if len(w) >= 4 and w not in _GENERIC}
        hit = sorted(upw & words)
        if hit:
            out.append((1, {"name": s["name"], "why": f"made by {s['uploader']}"}))
            continue
        tw = {w for w in _words(s.get("title") or "") if len(w) >= 4 and not w.isdigit() and w not in _GENERIC}
        hit = sorted(tw & words)
        if hit:
            out.append((2 if len(hit) == 1 else 1.5, {"name": s["name"], "why": "its title says " +
                                                      ", ".join(f"'{w}'" for w in hit[:3])}))
    if any(rk <= 1 for rk, _ in out):                  # the creator found: title-only matches would be noise
        out = [t for t in out if t[0] <= 1]
    return [x for _, x in sorted(out, key=lambda t: t[0])][:4]


def style_text(r: dict) -> list[str]:
    """The lines MCP prompts(id) / prompts.py show adds for a prompt's style: each linked reference measured, or the
    analysed references it seems to mean."""
    from . import knowledge as KN
    L = []
    for n in r.get("style_refs") or []:
        s = KN.style(n)
        L.append(f"  style from your reference {n}: " + (f"{s['title']}" + (f" by {s['uploader']}" if s.get("uploader")
                                                                             else "") + f" ({s['category_label']}) | "
                                                         f"{s['line']} | Claude reviewed {s['reviewed']}/{s['effects']}"
                                                         f" effects, the user gave {s['verdicts']} verdicts"
                                                         if s else "(not analysed on this PC any more)"))
    if r.get("kind") in STYLE_KINDS:
        sug = suggest_refs(r.get("text", ""), all_styles(), r.get("style_refs") or [])
        if sug:
            L.append("  analysed references it may mean (not linked): "
                     + "; ".join(f"{x['name']} ({x['why']})" for x in sug))
    return L


def all_styles() -> list[dict]:
    """knowledge.style() of every analysed reference (self-test videos left out)."""
    from . import knowledge as KN
    from .util import ANALYSIS
    if not ANALYSIS.exists():
        return []
    out = []
    for d in sorted(ANALYSIS.iterdir(), key=lambda p: p.name.lower()):
        if d.is_dir() and not d.name.startswith("synthetic_") and ".." not in d.name:
            s = KN.style(d.name)
            if s:
                out.append(s)
    return out


def set_style(pid: str, names: list[str]) -> dict:
    """Link analysed references to a prompt as its style (the card's *Style like*; [] = none)."""
    from . import knowledge as KN
    names = [str(n) for n in dict.fromkeys(names or []) if str(n).strip()]
    for n in names:
        if not KN.style(n):
            raise ValueError(f"no analysed reference {n!r} - analyse it first (References)")
    return update(pid, style_refs=names[:5])


# ------------------------------------------------------------------------------------------------ the paste format
TEMPLATE = """PROMPT 1
kind: shot
model: Seedance 2.0 on Higgsfield
source: tested by me
result: good - one line on what came out
text:
<the prompt itself, any number of lines>

PROMPT 2
kind: hook
source: creator: <name> <link>
result: -
text:
<...>
"""
_URL = re.compile(r"https?://\S+")


def _source(v: str) -> dict:
    s = v.strip()
    low = s.lower()
    if low.startswith("creator"):
        rest = s.split(":", 1)[1].strip() if ":" in s else s[len("creator"):].strip()
        m = _URL.search(rest)
        link = m[0] if m else ""
        return {"type": "creator", "creator": _URL.sub("", rest).strip(" -,"), "link": link}
    if low.startswith("tested") or low in ("me", "mine", "my own", "own"):
        return {"type": "tested"}
    if low.startswith(("written", "claude")):
        return {"type": "written"}
    m = _URL.search(s)
    if m:                                                       # just a link (or a name + link): a creator's prompt
        return {"type": "creator", "creator": _URL.sub("", s).strip(" -,"), "link": m[0]}
    raise ValueError(f"source: 'tested by me' or 'creator: <name> <link>' (got {v!r})")


def _result(v: str) -> dict:
    s = v.strip()
    m = re.match(r"(good|ok|okay|bad)\b\s*[-:,]?\s*(.*)$", s, re.I | re.S)
    if m:
        return {"rating": "ok" if m[1].lower() == "okay" else m[1].lower(), "note": m[2].strip()}
    if s in ("", "-", "?", "none", "untested", "not tested"):
        return {"rating": None, "note": ""}
    return {"rating": None, "note": s}


_HEAD = re.compile(r"(?im)^\s*PROMPT\s*#?\s*\d*\s*:?\s*$")
_KEY = re.compile(r"\s*(kind|title|model|source|result|tags)\s*:\s*(.*)$", re.I)
# words that say what a text is for (guess_kind): movement = a video model's shot, still words = an image, the look
# (camera, light) = either, a person talking = a hook or a script. Some Spanish: creators' guides mix languages.
_MOTION = re.compile(r"\b(dolly|dollies|pan|pans|panning|tilts?|tracking|handheld|drone|zoom(s|ing)?|orbit(s|ing)?|"
                     r"slow[- ]motion|fps|seconds?|\d+\s?s|cut to|transition|moves?|moving|movement|walks?|walking|"
                     r"runs?|running|turns?|clips?|footage|videos?|v[ií]deo|movimiento|graba[rn]?|c[aá]mara lenta)\b|"
                     r"@video", re.I)
_LOOK = re.compile(r"\b(camera|c[aá]mara|shots?|close-?ups?|wide|lens|\d{2,3}\s?mm|cinematic|scene|light(ing)?|"
                   r"iluminaci[oó]n|9:16|16:9)\b", re.I)
_STILL = re.compile(r"\b(photo(graph)?s?|portrait|image|still|render(ed)?|illustration|poster|thumbnail|8k|"
                    r"composition|texture|studio|depth of field|bokeh|foto|imagen)\b", re.I)
_BRIEF = re.compile(r"\b(timeline|l[ií]nea de tiempo|resolve|da ?vinci|premiere|capcut|edit|edits|editing|edita|"
                    r"edites|editar|edici[oó]n|b-?roll|luts?|grad(e|ing)|etalonaje|subt[ií]tulos|captions|cortes|"
                    r"cuts|montaje|transitions?|transiciones|sfx|efectos de sonido|sound effects|m[uú]sica|music|"
                    r"render|export(ar)?|proyecto|project|clips|footage|grabaciones|tomas|vlog|storytelling|"
                    r"motion ?graphics|motion labs?|gui[oó]n|hook|retenci[oó]n|retention)\b", re.I)
_SPOKEN = re.compile(r"\b(i|i'm|i've|you|you're|your|we|my|me|today|guys|subscribe|follow|comment)\b", re.I)


_ES = re.compile(r"\b(quiero|que|el|la|los|las|con|para|una?|estilo|video|crees|edita|haz)\b", re.I)
_FILLER = re.compile(r"^(quiero que|quiero|necesito que|necesito|me gustar[ií]a que|i want you to|i want|i'd like you to|"
                     r"please|por favor|can you|could you|you are|eres|act as|create|generate|make|write|haz|crea|"
                     r"genera|escribe|edita|edit)\b[\s,:]*", re.I)
_FORMATS = ["music video", "talking head", "videoclip", "vlog", "reel", "short", "tiktok", "tutorial", "trailer",
            "documental", "documentary", "anuncio", "ad", "podcast", "intro", "story", "storytime"]


def auto_title(text: str, kind: str = "") -> str:
    """A short title for a prompt nobody titled yet (Claude's check writes a better one): for a brief the footage
    folder, the format and the style it names ("Londres Día 1 · vlog · estilo Clavero"), else the first words that
    say what it makes, without "I want you to" / "Quiero que" / "@video1:"."""
    t = re.sub(r"https?://\S+|@\w+\s*:?", " ", str(text or "")).strip()
    if not t:
        return "Untitled prompt"
    es = len(_ES.findall(t[:600])) >= 4
    if kind == "brief":
        parts = []
        m = re.search(r"(\w+)\s*[\\/]\s*(\w+(?:[ _-]\d+)?)", t)           # a footage folder: Londres\Día 1
        if m:
            parts.append(f"{m[1]} {m[2]}")
        low = t.lower()
        fmt = next((f for f in _FORMATS if re.search(rf"\b{re.escape(f)}\b", low)), "")
        if fmt:
            parts.append(fmt)
        m = re.search(r"(?:al estilo|en el estilo|con el estilo|in the style|style)(?: (?:vlog|video|de los videos|of the videos))?"
                      r" (?:de|of|like)\s+(?:la |el |los |the )?([\w][\w'-]*(?: [A-Z][\w'-]*)?)", t, re.I)
        if m:
            parts.append(("estilo " if es else "style ") + m[1][:1].upper() + m[1][1:])
        if len(parts) >= 2:
            s = " · ".join(parts)[:70]
            return s[:1].upper() + s[1:]
    first = re.split(r"(?<=[.!?])\s|\n", t, maxsplit=1)[0]
    first = re.sub(r"[\"“”*#_>\[\]{}]", "", first).strip()
    for _ in range(3):
        first = _FILLER.sub("", first).strip()
    head = re.split(r"[:;—–]| - ", first, maxsplit=1)[0].strip()      # "Edita mi viaje a Roma: un reel..." -> the part
    if len(head.split()) >= 2:                                          # before the colon names it best
        first = head
    words = first.split()
    s = " ".join(words[:8]).strip(" ,.;:-")
    if len(words) > 8:
        s += "…"
    return (s[:1].upper() + s[1:]) if s else "Untitled prompt"


def guess_kind(text: str) -> str:
    """shot / image / hook / script / brief from the words - the Add dialog's default; the user can pick another
    (2026-10-12, the 29 prompts in the library: 28 right; the user's Spanish vlog brief: brief)."""
    motion, look, still, spoken = (len(rx.findall(text or "")) for rx in (_MOTION, _LOOK, _STILL, _SPOKEN))
    hits = [m.group(0).lower() for m in _BRIEF.finditer(text or "")]
    # instructions to make / edit a whole video: several different editing words, more than words said to a viewer
    # (a talking script about editing says "editing" a lot, to "you guys")
    if len(set(hits)) >= 4 and len(hits) > spoken and len(hits) >= motion + still:
        return "brief"
    if motion + look + still >= max(2, spoken):                 # a description for a model
        return "image" if still and not motion else "shot"
    return "hook" if len((text or "").split()) <= 40 else "script"


def parse_paste(text: str, kind: str = "", source: dict | None = None, file: str = "",
                tags: list | None = None) -> list[dict]:
    """What the Add dialog gets -> records for `add`. Any text (0.3.3): one prompt, or several when lines of only
    '---' separate them; kind = `kind` or guessed from the words; source = `source` (default: tested by you) + the
    attached `file`; `tags` = what it is for (vlog, talking head, SFX, transitions...). The older format still works - blocks that start with 'PROMPT <n>', `key: value` lines (kind,
    model, source, result, title, tags), then the prompt (after a 'text:' line, or simply after the key lines).
    Raises ValueError naming the prompt that is wrong; nothing is saved then."""
    text = str(text or "").replace("\r", "")
    if kind and kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)} (got {kind!r})")
    src = {**(source or {"type": "tested"}), **({"file": file} if file else {})}
    tags = [str(x).strip().lower() for x in (tags or []) if str(x).strip()][:12]
    if not _HEAD.search(text):
        parts = [p.strip() for p in re.split(r"(?m)^\s*-{3,}\s*$", text) if p.strip()]
        out = [{"kind": kind or guess_kind(p), "text": p, "source": dict(src), "tags": list(tags)} for p in parts]
        for n, r in enumerate(out, 1):
            try:
                _check(r)
            except ValueError as e:
                raise ValueError(f"prompt {n}: {e}") from None
        if not out:
            raise ValueError("nothing to save - paste a prompt or attach a file")
        return out
    out = []
    for n, b in enumerate([b for b in _HEAD.split(text) if b.strip()], 1):
        m = re.search(r"(?im)^\s*(?:prompt )?text\s*:", b)
        if m:
            head, body = b[:m.start()], b[m.end():]
        else:                                                   # no 'text:' line: the key lines, then the prompt
            lines = b.split("\n")
            i = 0
            while i < len(lines) and (not lines[i].strip() or _KEY.match(lines[i])):
                i += 1
            head, body = "\n".join(lines[:i]), "\n".join(lines[i:])
        kv = {}
        for line in head.splitlines():
            m = re.match(r"\s*([a-z ]+?)\s*:\s*(.*)$", line, re.I)
            if m:
                kv[m[1].lower()] = m[2].strip()
        try:
            k = kv.get("kind", "").lower().strip()
            k = {"shots": "shot", "video": "shot", "images": "image", "photo": "image", "hooks": "hook",
                 "scripts": "script"}.get(k, k) or kind or guess_kind(body)
            rec = {"kind": k, "title": kv.get("title", "") or auto_title(body, k), "model": kv.get("model", "").strip(" -") or "",
                   "source": {**_source(kv["source"]), **({"file": file} if file else {})} if kv.get("source")
                   else dict(src), "result": _result(kv.get("result", "")),
                   "text": body.strip(),
                   "tags": [t.strip() for t in kv.get("tags", "").split(",") if t.strip()] + list(tags)}
            if rec["model"].lower() in ("none", "n/a"):
                rec["model"] = ""
            _check(rec)
        except ValueError as e:
            raise ValueError(f"prompt {n}: {e}") from None
        out.append(rec)
    return out


def import_paste(text: str, kind: str = "", source: dict | None = None, file: str = "",
                 tags: list | None = None) -> list[dict]:
    """Parse the whole paste first (nothing is saved when one prompt is wrong), then save every prompt."""
    return [add(r) for r in parse_paste(text, kind, source, file, tags)]


def path_of(pid: str) -> Path:
    """The file of a saved prompt (the app's Delete moves it to the Recycle Bin)."""
    p = _path(pid)
    if not p.exists():
        raise ValueError(f"no prompt {pid}")
    return p


# ------------------------------------------------------------------------------------------------ attached files
FILES = HOME / "files"                                  # what the user attached (the prompts' `source.file`)
FILE_TYPES = (".txt", ".md", ".docx", ".pdf")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def file_text(p: Path) -> str:
    """The text of a .txt / .md / .docx file ("" for a PDF - Claude reads those: no PDF library in the lab)."""
    ext = p.suffix.lower()
    if ext in (".txt", ".md"):
        return p.read_bytes().decode("utf-8-sig", errors="replace").replace("\r", "").strip()
    if ext == ".docx":                                  # a zip; the text is in word/document.xml, one <w:p> per paragraph
        import xml.etree.ElementTree as ET
        import zipfile
        try:
            with zipfile.ZipFile(p) as z:
                if z.getinfo("word/document.xml").file_size > 50_000_000:
                    raise ValueError("this .docx is too big to read")
                root = ET.fromstring(z.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError(f"{p.name} is not a Word document that can be read") from None
        paras = ["".join((e.text or "") if e.tag == _W + "t" else "\t" if e.tag == _W + "tab" else
                         "\n" if e.tag in (_W + "br", _W + "cr") else "" for e in para.iter())
                 for para in root.iter(_W + "p")]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(paras)).strip()
    return ""


def save_file(name: str, data: bytes) -> dict:
    """An attached file -> knowledge\\local\\prompts\\files\\ (the same file again is not stored twice) ->
    {file, rel, text}: `text` = what file_text() reads ("" for a PDF)."""
    ext = Path(name).suffix.lower()
    if ext not in FILE_TYPES:
        raise ValueError(f"attach a {', '.join(FILE_TYPES)} file (got {Path(name).name!r})")
    stem = safe_name(Path(name).stem)
    with _LOCK:
        FILES.mkdir(parents=True, exist_ok=True)
        dest, n = FILES / f"{stem}{ext}", 2
        while dest.exists() and dest.read_bytes() != data:
            dest, n = FILES / f"{stem}_{n}{ext}", n + 1
        if not dest.exists():
            dest.write_bytes(data)
    return {"file": dest.name, "rel": f"{FOLDER}/files/{dest.name}", "text": file_text(dest)}


# what a prompt makes - a picture or clip of the result (the user's, or the creator's example): the pop-up shows them,
# the first is the card's picture. knowledge\local\prompts\examples\, private like the prompts.
EXAMPLES = HOME / "examples"
EXAMPLE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm")
MAX_EXAMPLES = 6


def add_example(pid: str, name: str, data: bytes) -> dict:
    ext = Path(name).suffix.lower()
    if ext not in EXAMPLE_TYPES:
        raise ValueError(f"a picture or clip: {', '.join(EXAMPLE_TYPES)} (got {Path(name).name!r})")
    if not data:
        raise ValueError("the file is empty")
    with _LOCK:
        r = get(pid)
        ex = list(r.get("examples") or [])
        if len(ex) >= MAX_EXAMPLES:
            raise ValueError(f"up to {MAX_EXAMPLES} per prompt - remove one first")
        EXAMPLES.mkdir(parents=True, exist_ok=True)
        dest = EXAMPLES / f"{pid}_{_dt.datetime.now():%Y%m%d-%H%M%S}_{safe_name(Path(name).stem)[:40] or 'example'}{ext}"
        dest.write_bytes(data)
        return update(pid, examples=ex + [dest.name])


def remove_example(pid: str, file: str) -> tuple[dict, Path | None]:
    """Takes it off the prompt; returns the file (the app moves it to the Recycle Bin)."""
    with _LOCK:
        ex = list(get(pid).get("examples") or [])
        if file not in ex:
            raise ValueError(f"{file!r} is not an example of {pid}")
        r = update(pid, examples=[x for x in ex if x != file])
    p = EXAMPLES / Path(file).name
    return r, p if p.exists() else None


def overview() -> dict:
    """What the app's Prompts page shows."""
    items = load_all()
    for r in items:                                     # older prompts saved without a title (Claude's check adds one)
        if not r.get("title"):
            r["title_auto"] = auto_title(r.get("text", ""), r.get("kind", ""))
    return {"kinds": [{"id": k, "label": v, "count": sum(1 for r in items if r["kind"] == k),
                       "slots": SLOTS[k]} for k, v in KINDS.items()],
            "items": items, "template": TEMPLATE, "folder": FOLDER, "help": KIND_HELP, "statuses": list(STATUSES)}


def describe(r: dict, full: bool = False) -> str:
    """A prompt as text for Claude (MCP / CLI)."""
    src = r.get("source") or {}
    who = {"tested": "tested by the user", "written": "written by Claude" + (
        f" from {', '.join(r.get('made_from') or [])}" if r.get("made_from") else ""),
           "creator": f"creator {src.get('creator') or '?'} {src.get('link') or ''}".strip()}.get(src.get("type"), "?")
    res, rv = r.get("result") or {}, r.get("review") or {}
    L = [f"{r['id']} [{r['kind']}] {r.get('title') or '(no title)'} | {who}"
         + (f" | model {r['model']}" if r.get("model") else "")
         + f" | user's rating {res.get('rating') or 'none'}" + (f" ({res['note']})" if res.get("note") else "")
         + (f" | Claude's review {rv['stars']}/5" if rv.get("stars") is not None else "")
         + (f" | pattern {r['pattern']}" if r.get("pattern") else "")
         + (f" | workflow '{r['workflow']}' step {r.get('step') or '?'}" if r.get("workflow") else "")]
    if rv.get("why") and full:
        L.append(f"  review: {rv['why']}" + (f" Fix: {rv['fix']}" if rv.get("fix") else ""))
    if r.get("notes") and full:
        L.append(f"  how to use: {r['notes']}")
    if r.get("structure") and full and any(x.get("status") for x in r["structure"]):
        L.append("  Claude's check (part: status - what it says - tip):")      # 0.3.4: what Optimize starts from
        L += [f"    {x['slot']}: {x.get('status') or '-'} - {x['text'] or '(not said)'}"
              + (f" - tip: {x['tip']}" if x.get("tip") else "") for x in r["structure"]]
    elif r.get("structure"):
        L.append("  structure: " + " > ".join(f"{x['slot']}: {x['text']}" for x in r["structure"]))
    elif full:
        L.append("  structure: not split yet")
    if full:
        if r.get("wishes"):
            L.append("  what the user wants (wins over the tips): "
                     + " | ".join(f"{k}: {v}" for k, v in r["wishes"].items()))
        L += style_text(r)
    elif r.get("style_refs"):
        L.append("  style from: " + ", ".join(r["style_refs"]))
    text = r.get("text", "")
    L.append("  text: " + (text if full or len(text) <= 300 else text[:300] + " ..."))
    return "\n".join(L)
