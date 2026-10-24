"""The prompt library (0.4): proven prompts per kind, each split into its structure, so Claude can write a new one in
a structure that already worked (`/write-prompt`).

One home: knowledge\\local\\prompts\\<kind>\\<id>.json (private to this PC; sharing your own prompts comes later).
A prompt = the text, where it came from (`tested` by you, a `creator`'s public prompt + link, or `written` by
Claude from examples), the model (shots), your rating of what it made (good / ok / bad + a note), and its structure
(ordered slots with the words that filled them; Claude writes it when the prompt is added). Used by
tools\\prompts.py, the app's prompt library (Generate) and MCP `prompts()`.

Claude's check, verified (2026-10-18): `verify_check()` is the one gate for every check Claude saves (tools\\prompts.py
annotate / import, the text sets' textsets.save_check): every quoted part must be found in THIS text (the saved quote
= the original words + their character positions `at`), every part of the kind is a row or `skipped` with a reason, a
part the measured script check flags is not "clear" without a reason. `verify_source()` = a prompt Claude copies out
of an attached file must be in that file. The user's verdict on each part of Claude's check = `verdicts`.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import time as _time
import re
import threading
import unicodedata
from pathlib import Path

from . import i18n as I18N
from .util import LAB, read_json, safe_name, write_json

FOLDER = "knowledge/local/prompts"                      # relative to the lab (the app's "Folder" button)
HOME = LAB / FOLDER
KINDS = {"brief": "Brief for Claude", "shot": "Video-model shot", "image": "Image (still / start frame)",
         "hook": "Hook (first 3 s)", "script": "Talking script",
         "title": "Title & thumbnail"}      # brief first: the user's main use (0.3.4); title = 0.4.3 packaging
# what each kind is, in words (the Add dialog and the kind chips' tooltips)
KIND_HELP = {"shot": "one shot of AI video - for Seedance, Kling, Higgsfield...",
             "image": "a still or a start frame - for Nano Banana, GPT Image, Kling Image...",
             "hook": "the first 3 seconds you say or show",
             "script": "the words you say on camera",
             "brief": "you tell Claude how to make or edit a video: length, feel, colour, pacing, SFX, graphics...",
             "title": "the titles and thumbnail ideas for a video - before you film, or for the final post"}
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
    # a talking script (Prepare, `/write-script`: .claude\skills\write-script\guidelines.md): in the order it is said
    "script": ["hook", "promise", "problem", "points", "re-hooks", "proof", "payoff", "call to action", "on screen"],
    # 0.3.4: a brief = what Claude needs to make a whole video; Claude's check marks each clear / vague / missing.
    # In the order a video is made (the app groups them: the plan, the edit, sound, look & text, finish); effects,
    # voice & audio and ending added after the user asked "what other parts should Claude check?"
    "brief": ["format & length", "story & hook", "feel / style", "footage", "order & structure",
              "pacing & cuts", "transitions", "effects",
              "voice & audio", "music", "sfx",
              "colour", "motion graphics", "captions & text",
              "ending", "deliverable", "questions first"],
    # 0.4.3: a video's packaging (`/write-title`, .claude\skills\write-title\guidelines.md) - the record's own fields
    # `titles` / `concepts` / `hook` hold the content; these slots are Claude's check of it
    "title": ["titles", "thumbnail", "words on it", "shot to film", "colours", "hook"],
}
STATUSES = ("clear", "vague", "missing")                # Claude's check of one slot (structure[i].status)
VERDICTS = ("correct", "partly", "wrong")               # the USER's verdict on Claude's check of one slot (verdicts)
HOOK_PATTERNS = ["question", "bold claim", "number", "story", "contrarian", "demo", "curiosity gap", "call-out"]
# title patterns (`/write-title`: about 10 titles, each in a different one; a guide, other names are allowed)
TITLE_PATTERNS = ["curiosity gap", "number / result", "how-to", "warning / mistake", "question", "I tried",
                  "before -> after", "contrarian", "challenge", "list", "story", "call-out"]
TITLE_MAX = 100                                         # YouTube refuses a longer title (support.google.com 57404)
_LOCK = threading.RLock()


def _today() -> str:
    return _dt.date.today().isoformat()


def _path(pid: str) -> Path:
    m = re.fullmatch(r"(shot|image|hook|script|brief|title)-(\d{3,})", str(pid))
    if not m:
        raise ValueError(f"not a prompt id: {pid!r} (like shot-001, image-002, hook-003, script-004, title-005)")
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


def count(kinds=None) -> int:
    """How many prompts the library has (file count, nothing parsed - Home's cards; kinds = only those)."""
    return sum(len(list((HOME / k).glob(f"{k}-*.json"))) for k in (kinds or KINDS))


def get(pid: str) -> dict:
    p = _path(pid)
    if not p.exists():
        raise ValueError(I18N.t("no prompt {id}", id=pid))
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


def _last_path(kind: str) -> Path:
    return HOME / kind / "_last_id.txt"


def next_id(kind: str) -> str:
    """The next number of a kind - never one given before (2026-10-24: a deleted script-014's number came back for
    the next script, which then looked like the old one - its NEW badge, made_from links). _last_id.txt keeps the
    highest number ever given."""
    nums = [int(p.stem.split("-")[1]) for p in (HOME / kind).glob(f"{kind}-*.json") if p.stem.split("-")[1].isdigit()]
    try:
        nums.append(int(_last_path(kind).read_text(encoding="utf-8").strip()))
    except (OSError, ValueError):
        pass
    return f"{kind}-{max(nums, default=0) + 1:03d}"


def _given(pid: str) -> None:
    kind, n = pid.rsplit("-", 1)
    _last_path(kind).parent.mkdir(parents=True, exist_ok=True)
    _last_path(kind).write_text(str(int(n)), encoding="utf-8")


def created(r: dict) -> float:
    """When a prompt was saved (seconds): "created" (since 2026-10-24), else its file's creation time."""
    if r.get("created"):
        return float(r["created"])
    try:
        st = _path(r["id"]).stat()
        return getattr(st, "st_birthtime", None) or st.st_ctime
    except (OSError, ValueError, KeyError):
        return 0.0


def _check(r: dict) -> None:
    if r.get("kind") not in KINDS:
        raise ValueError(I18N.t("kind must be one of {kinds} (got {got})", kinds=", ".join(KINDS),
                                got=repr(r.get("kind"))))
    if r.get("kind") == "title":
        _check_title(r)
    if not str(r.get("text", "")).strip() and not (r.get("kind") == "title" and (r.get("titles") or r.get("concepts"))):
        raise ValueError(I18N.t("a prompt needs its text"))
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
    # 2026-10-18: the parts Claude left out on purpose (with why), and the user's verdict per part of Claude's check -
    # their part names are checked against the kind by verify_check (a kind change keeps them as they were)
    sk = r.get("skipped")
    if sk is not None and not (isinstance(sk, dict) and all(isinstance(k, str) and k.strip() and isinstance(v, str)
                                                             and v.strip() for k, v in sk.items())):
        raise ValueError("skipped = {part: why it is not part of this prompt}")
    vd = r.get("verdicts")
    if vd is not None and not (isinstance(vd, dict) and all(isinstance(k, str) and k.strip() and v in VERDICTS
                                                            for k, v in vd.items())):
        raise ValueError(f"verdicts = {{part: {' / '.join(VERDICTS)}}} (the user's verdict on Claude's check of it)")
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
    if r.get("request") and not re.fullmatch(r"req-\d{3,}", str(r["request"])):
        raise ValueError("request = the Prepare request it was written from (req-001, ...)")
    if r.get("project") and safe_name(str(r["project"])) != r["project"]:
        raise ValueError("project = the video's folder name in projects (its final package)")


# ------------------------------------------------------------------------------------------------ title & thumbnail
def _check_title(r: dict) -> None:
    """A title record (0.4.3): titles [{text, pattern, chars}], concepts [{id, sketch, words, shot, colours}], hook,
    chosen (the final title), and its link: request (req-NNN, *Title & thumbnail first*) and / or project (the video
    being packaged)."""
    ts = r.get("titles") or []
    if not isinstance(ts, list) or not all(isinstance(t, (dict, str)) and str((t.get("text") if isinstance(t, dict)
                                                                              else t) or "").strip() for t in ts):
        raise ValueError("titles = a list of {text, pattern}")
    for t in ts:
        text = str(t.get("text") if isinstance(t, dict) else t).strip()
        if len(text) > TITLE_MAX:
            raise ValueError(f"title over {TITLE_MAX} characters (YouTube refuses it): {text[:60]!r}...")
    cs = r.get("concepts") or []
    if not isinstance(cs, list) or not all(isinstance(c, dict) and str(c.get("id") or "").strip() for c in cs):
        raise ValueError("concepts = a list of {id: A, sketch, words, shot, colours}")
    ids = [str(c["id"]).strip().upper() for c in cs]
    if len(set(ids)) != len(ids):
        raise ValueError("each thumbnail concept needs its own id (A, B, C)")
    if not isinstance(r.get("hook") or "", str):
        raise ValueError("hook = the first 3 s, as text")


def clean_titles(ts) -> list[dict]:
    """Titles as saved: text trimmed, the pattern, chars counted here (never trusted from the caller)."""
    out = []
    for t in ts or []:
        if isinstance(t, str):
            t = {"text": t}
        if not isinstance(t, dict):
            continue
        text = " ".join(str(t.get("text") or "").split())
        if text:
            out.append({"text": text, "pattern": str(t.get("pattern") or "").strip(), "chars": len(text),
                        **({"note": str(t["note"]).strip()} if t.get("note") else {})})
    return out


def clean_concepts(cs) -> list[dict]:
    out = []
    for c in cs or []:
        if isinstance(c, dict):
            out.append({"id": str(c.get("id") or "").strip().upper(), "sketch": str(c.get("sketch") or "").strip(),
                        "words": " ".join(str(c.get("words") or "").split()), "shot": str(c.get("shot") or "").strip(),
                        "colours": str(c.get("colours") or "").strip(),
                        **({k: str(c[k]).strip() for k in ("for", "title") if c.get(k)})})
    return out


def title_text(r: dict) -> str:
    """A title record as plain text (its `text`: what the app's card shows and Copy copies)."""
    L = ["TITLES"] + [f"{i}. {t['text']}" + (f"  ({t['pattern']})" if t.get("pattern") else "")
                      for i, t in enumerate(r.get("titles") or [], 1)]
    for c in r.get("concepts") or []:
        L += ["", f"THUMBNAIL {c['id']}" + (f" - for title {c['title']}" if c.get("title") else ""),
              f"Sketch: {c.get('sketch') or '-'}", f"Words on it: {c.get('words') or '-'}",
              f"Shot to film: {c.get('shot') or '-'}", f"Colours: {c.get('colours') or '-'}"]
    if r.get("hook"):
        L += ["", "HOOK (first 3 s)", r["hook"]]
    return "\n".join(L).strip()


def describe_title(r: dict) -> list[str]:
    """The lines describe() prints for a title record: every title with its pattern and length on a phone, the
    thumbnail concepts, the hook, what it is linked to."""
    L = []
    link = [f"request {r['request']}" if r.get("request") else "",
            f"the video projects\\{r['project']}" if r.get("project") else ""]
    if any(link):
        L.append("  for: " + ", ".join(x for x in link if x))
    if r.get("chosen"):
        L.append(f"  final title: {r['chosen']} ({len(r['chosen'])} characters)")
    ts = r.get("titles") or []
    if ts:
        L.append(f"  titles ({len(ts)}; a phone shows about 50-60 characters - a rule of thumb):")
        for i, t in enumerate(ts, 1):
            n = t.get("chars") or len(t["text"])
            L.append(f"    {i:2}. {t['text']}  [{t.get('pattern') or 'no pattern'} | {n} chars"
                     + ("" if n <= 60 else " - may be cut on a phone") + "]" + (f" - {t['note']}" if t.get("note") else ""))
    for c in r.get("concepts") or []:
        L.append(f"  thumbnail {c['id']}" + (f" (for title {c['title']})" if c.get("title") else "") + ":")
        L += [f"      {k}: {c.get(v) or '-'}" for k, v in (("sketch", "sketch"), ("words on it", "words"),
                                                              ("shot to film", "shot"), ("colours", "colours"))]
        nw = len(str(c.get("words") or "").split())
        if nw and not 2 <= nw <= 4:
            L.append(f"      ({nw} words on it - the rule of thumb is 2-4)")
    if r.get("hook"):
        L.append(f"  hook (first 3 s, keeps the title's promise): {r['hook']}")
    return L


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
    style_refs (analysed references whose measured style it follows), request (a script written from the user's
    answers in Prepare: its req-NNN)."""
    r = {"kind": rec.get("kind"), "title": str(rec.get("title") or "").strip(), "text": str(rec.get("text") or "").strip(),
         "model": str(rec.get("model") or "").strip(), "source": dict(rec.get("source") or {}),
         "result": {"rating": None, "note": "", **(rec.get("result") or {})},
         "structure": rec.get("structure") or None, "pattern": rec.get("pattern") or "",
         "tags": list(rec.get("tags") or []), "made_from": list(rec.get("made_from") or []),
         "review": _review(rec.get("review")), "workflow": str(rec.get("workflow") or "").strip(),
         "step": rec.get("step"), "notes": str(rec.get("notes") or "").strip(),
         "style_refs": list(rec.get("style_refs") or []), "added": _today(), "updated": _today()}
    if rec.get("request"):
        r["request"] = str(rec["request"]).strip()
    if rec.get("skipped"):                              # 2026-10-18: the parts Claude's check left out, with why
        r["skipped"] = dict(rec["skipped"])
    if r["kind"] == "title":                            # 0.4.3: the packaging's own fields; text = them in words
        r.update(titles=clean_titles(rec.get("titles")), concepts=clean_concepts(rec.get("concepts")),
                 hook=str(rec.get("hook") or "").strip(), chosen=" ".join(str(rec.get("chosen") or "").split()))
        if rec.get("project"):
            r["project"] = str(rec["project"]).strip()
        if not r["text"]:
            r["text"] = title_text(r)
    _check(r)
    with _LOCK:
        r["id"] = next_id(r["kind"])
        r["created"] = round(_time.time(), 3)
        write_json(_path(r["id"]), {"id": r["id"], **r}, indent=1)
        _given(r["id"])
    return get(r["id"])


def update(pid: str, **changes) -> dict:
    """Change fields of a saved prompt: title, model, structure (Claude's check: per slot what the prompt says +
    status clear / vague / missing + a tip; save it through verify_check), skipped (the parts that are not part of
    this prompt: {slot: why}), pattern, tags, workflow, step, notes, review (Claude's stars), wishes (the user's:
    {slot: what I want} - read by `/write-prompt optimize`), verdicts (the user's: {slot: correct | partly | wrong} =
    is Claude's check of that part right; "" clears one), style_refs (analysed references whose measured style the
    prompt follows), rating + note (the user's) - the text and the source stay as they were added."""
    with _LOCK:
        r = get(pid)
        for k in ("title", "model", "structure", "pattern", "tags", "workflow", "step", "notes", "wishes",
                  "style_refs", "examples", "skipped"):
            if k in changes and changes[k] is not None:
                r[k] = changes[k]
        if changes.get("verdicts") is not None:         # the whole set of the user's verdicts, like wishes
            r["verdicts"] = {str(k): v for k, v in dict(changes["verdicts"]).items() if v}
        if changes.get("review") is not None:
            r["review"] = _review(changes["review"])
        if r.get("kind") == "title":                    # a title record's content (its text follows it)
            touched = False
            for k, fn in (("titles", clean_titles), ("concepts", clean_concepts)):
                if changes.get(k) is not None:
                    r[k], touched = fn(changes[k]), True
            for k in ("hook", "chosen", "project"):
                if changes.get(k) is not None:
                    r[k] = str(changes[k]).strip() if k == "hook" else " ".join(str(changes[k]).split())
                    touched = touched or k == "hook"
            if touched:
                r["text"] = title_text(r)
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
        raise ValueError(I18N.t("kind must be one of {kinds} (got {got})", kinds=", ".join(KINDS), got=repr(kind)))
    with _LOCK:
        r = get(pid)
        if r["kind"] == kind:
            return r
        old = _path(pid)
        r.update(kind=kind, id=next_id(kind), updated=_today())
        _check(r)
        write_json(_path(r["id"]), r, indent=1)
        _given(r["id"])
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
            out.append((0, {"name": s["name"], "why": I18N.t("made by {name}", name=s["uploader"])}))
            continue
        upw = {w for w in up.split() if len(w) >= 4 and w not in _GENERIC}
        hit = sorted(upw & words)
        if hit:
            out.append((1, {"name": s["name"], "why": I18N.t("made by {name}", name=s["uploader"])}))
            continue
        tw = {w for w in _words(s.get("title") or "") if len(w) >= 4 and not w.isdigit() and w not in _GENERIC}
        hit = sorted(tw & words)
        if hit:
            out.append((2 if len(hit) == 1 else 1.5, {"name": s["name"], "why": I18N.t(
                "its title says {words}", words=", ".join(f"'{w}'" for w in hit[:3]))}))
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
            raise ValueError(I18N.t("no analysed reference {name} - analyse it first (References)", name=repr(n)))
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
    raise ValueError(I18N.t("source: 'tested by me' or 'creator: <name> <link>' (got {got})", got=repr(v)))


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
        raise ValueError(I18N.t("kind must be one of {kinds} (got {got})", kinds=", ".join(KINDS), got=repr(kind)))
    src = {**(source or {"type": "tested"}), **({"file": file} if file else {})}
    tags = [str(x).strip().lower() for x in (tags or []) if str(x).strip()][:12]
    if not _HEAD.search(text):
        parts = [p.strip() for p in re.split(r"(?m)^\s*-{3,}\s*$", text) if p.strip()]
        out = [{"kind": kind or guess_kind(p), "text": p, "source": dict(src), "tags": list(tags)} for p in parts]
        for n, r in enumerate(out, 1):
            try:
                _check(r)
            except ValueError as e:
                raise ValueError(I18N.t("prompt {n}: {error}", n=n, error=e)) from None
        if not out:
            raise ValueError(I18N.t("nothing to save - paste a prompt or attach a file"))
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
            raise ValueError(I18N.t("prompt {n}: {error}", n=n, error=e)) from None
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
        raise ValueError(I18N.t("no prompt {id}", id=pid))
    return p


# ------------------------------------------------------------------------------------------------ attached files
FILES = HOME / "files"                                  # what the user attached (the prompts' `source.file`)
FILE_TYPES = (".txt", ".md", ".docx", ".pdf")
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def pdf_reader() -> bool:
    """Can MotionLab read a PDF's text itself? (pypdf, requirements.txt since 2026-10-18 - setup / the Update button
    install it; without it a PDF goes to Claude, as before)."""
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return False
    return True


def _pdf_text(p: Path) -> str:
    """A PDF's text by pypdf, page after page; "" when it is not installed, the file is locked / broken, or a scan
    (no text layer) - then Claude reads it."""
    try:
        import pypdf
    except ImportError:
        return ""
    try:
        rd = pypdf.PdfReader(str(p))
        if rd.is_encrypted:
            rd.decrypt("")
        pages = [(pg.extract_text() or "") for pg in rd.pages[:500]]
    except Exception:                                  # noqa: BLE001 - an unreadable PDF = Claude reads it
        return ""
    t = re.sub(r"[ \t]+\n", "\n", "\n\n".join(pages).replace("\r", ""))
    words = re.findall(r"[^\W_]+", t)
    if len(words) < 5 or sum(map(len, words)) / len(words) < 2.5:     # letters one by one / a scan: no usable text
        return ""
    return re.sub(r"\n{3,}", "\n\n", t).strip()[:2_000_000]


def file_text(p: Path) -> str:
    """The text of a .txt / .md / .docx file, and of a PDF when pypdf is installed ("" otherwise, or for a scan -
    Claude reads those)."""
    ext = p.suffix.lower()
    if ext == ".pdf":
        return _pdf_text(p)
    if ext in (".txt", ".md"):
        return p.read_bytes().decode("utf-8-sig", errors="replace").replace("\r", "").strip()
    if ext == ".docx":                                  # a zip; the text is in word/document.xml, one <w:p> per paragraph
        import xml.etree.ElementTree as ET
        import zipfile
        try:
            with zipfile.ZipFile(p) as z:
                if z.getinfo("word/document.xml").file_size > 50_000_000:
                    raise ValueError(I18N.t("this .docx is too big to read"))
                root = ET.fromstring(z.read("word/document.xml"))
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError(I18N.t("{name} is not a Word document that can be read", name=p.name)) from None
        paras = ["".join((e.text or "") if e.tag == _W + "t" else "\t" if e.tag == _W + "tab" else
                         "\n" if e.tag in (_W + "br", _W + "cr") else "" for e in para.iter())
                 for para in root.iter(_W + "p")]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(paras)).strip()
    return ""


def save_file(name: str, data: bytes) -> dict:
    """An attached file -> knowledge\\local\\prompts\\files\\ (the same file again is not stored twice) ->
    {file, rel, text}: `text` = what file_text() reads ("" for a PDF the lab cannot read)."""
    ext = Path(name).suffix.lower()
    if ext not in FILE_TYPES:
        raise ValueError(I18N.t("attach a {types} file (got {name})", types=", ".join(FILE_TYPES),
                                name=repr(Path(name).name)))
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
        raise ValueError(I18N.t("a picture or clip: {types} (got {name})", types=", ".join(EXAMPLE_TYPES),
                                name=repr(Path(name).name)))
    if not data:
        raise ValueError(I18N.t("the file is empty"))
    with _LOCK:
        r = get(pid)
        ex = list(r.get("examples") or [])
        if len(ex) >= MAX_EXAMPLES:
            raise ValueError(I18N.t("up to {n} per prompt - remove one first", n=MAX_EXAMPLES))
        EXAMPLES.mkdir(parents=True, exist_ok=True)
        dest = EXAMPLES / f"{pid}_{_dt.datetime.now():%Y%m%d-%H%M%S}_{safe_name(Path(name).stem)[:40] or 'example'}{ext}"
        dest.write_bytes(data)
        return update(pid, examples=ex + [dest.name])


def remove_example(pid: str, file: str) -> tuple[dict, Path | None]:
    """Takes it off the prompt; returns the file (the app moves it to the Recycle Bin)."""
    with _LOCK:
        ex = list(get(pid).get("examples") or [])
        if file not in ex:
            raise ValueError(I18N.t("{file} is not an example of {id}", file=repr(file), id=pid))
        r = update(pid, examples=[x for x in ex if x != file])
    p = EXAMPLES / Path(file).name
    return r, p if p.exists() else None


# ------------------------------------------------------------------------------------------------ Claude's check, verified
# 2026-10-18 (the user: "imagine i wanted to analize 10 prompts at the same time i could and it wouldnt allucinate"): a
# TOOL makes sure Claude's check quotes the text - not the skill's wording. Measured on this PC's 26 prompts the day
# before: 244 of 248 quotes were the text's own words; the other 4 were paraphrases or pieces stitched out of order,
# and the app showed them in quotes as what "your prompt says". Word lists stay evidence (slot_words): a guard
# "marked missing but the text names it" fired on 6 of 27 missing rows, all 6 wrongly.
QUOTE_MAX = 400                                         # characters of one part's quote: longer = shorten it with ...
PIECE_MIN = 3                                           # letters of a piece between two ...
_SAME = {**dict.fromkeys("‘’‚‛′´", "'"), **dict.fromkeys("“”„‟″«»", '"'), **dict.fromkeys("‐‑‒–—―−⁃", "-")}
_MARKS = set("*_`#>")                                   # markdown marks a quote may leave out
_TOK = re.compile(r"[^\W_]+")
# a part the measured script check (script.check) flags warn / bad is not "clear" unless Claude says why the rule does
# not apply (write-script's rule, now in code): the part -> the check's ids
SCRIPT_FLAGS = {"script": {"hook": ("hook", "pattern"), "re-hooks": ("rehooks",), "call to action": ("cta",),
                           "on screen": ("cues",), "proof": ("specifics",), "payoff": ("ending",)},
                "hook": {"opening line": ("hook",), "pattern": ("pattern",), "on screen": ("cues",)}}
_GENERIC_MODEL = set("ai model models image images video videos pro max plus mini turbo fast new the and on via with "
                     "for app tool hd".split())


def fold_map(text: str) -> tuple[str, list[int]]:
    """The text as quotes are matched: case, accents, curly quotes, dashes, NBSP, … (= ...) and markdown marks
    (* _ ` # >) folded away, whitespace collapsed -> (folded, idx), idx[i] = the position in `text` of folded
    character i - so a match is cut from the ORIGINAL words."""
    out: list[str] = []
    idx: list[int] = []
    space = True
    for i, c in enumerate(str(text or "")):
        if c in _MARKS:
            continue
        for d in unicodedata.normalize("NFKD", _SAME.get(c, c)):
            if unicodedata.combining(d):
                continue
            for e in d.casefold():
                if e.isspace():
                    if not space:
                        out.append(" ")
                        idx.append(i)
                    space = True
                else:
                    out.append(e)
                    idx.append(i)
                    space = False
    if out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def text_sha(text: str) -> str:
    """16 hex of the folded text: the same words in another case, accents or spacing = the same text (a text set
    re-uses the prompt the library has already)."""
    return hashlib.sha1(fold_map(text)[0].encode("utf-8")).hexdigest()[:16]


def _toks(s: str) -> list[str]:
    return _TOK.findall(fold_map(s)[0])


def _snip(s: str, n: int = 60) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _edges(qf: str) -> tuple[str, str]:
    """The punctuation a folded quote has before its first word and after its last ("(", "@", a full stop)."""
    ws = list(_TOK.finditer(qf))
    return (qf[:ws[0].start()].strip(), qf[ws[-1].end():].strip()) if ws else ("", "")


class _Text:
    """A text folded once, for many quotes: its words in order with their places in the original."""

    def __init__(self, text: str):
        self.text = str(text or "")
        self.folded, self.idx = fold_map(self.text)
        self.spans = [(m.start(), m.end()) for m in _TOK.finditer(self.folded)]
        self.words = [self.folded[a:b] for a, b in self.spans]
        self.where: dict[str, list[int]] = {}
        for k, w in enumerate(self.words):
            self.where.setdefault(w, []).append(k)

    def find(self, words: list[str], start: int = 0) -> int:
        """The first word number >= start where these words follow each other, or -1."""
        m = len(words)
        for k in self.where.get(words[0], ()) if words else ():
            if k >= start and self.words[k:k + m] == words:
                return k
        return -1

    def cut(self, k: int, m: int, lead: str = "", trail: str = "") -> tuple[int, int]:
        """Words k .. k+m-1 -> [start, end) in the original text, grown over the punctuation the quote has at its
        edges when the text has it there too."""
        s, e = self.idx[self.spans[k][0]], self.idx[self.spans[k + m - 1][1] - 1] + 1
        t = self.text
        while lead and s > 0:
            f = fold_map(t[s - 1])[0]
            if not f or not lead.endswith(f):
                break
            s, lead = s - 1, lead[:-len(f)]
        while trail and e < len(t):
            f = fold_map(t[e])[0]
            if not f or not trail.startswith(f):
                break
            e, trail = e + 1, trail[len(f):]
        return s, e

    def closest(self, words: list[str]) -> dict | None:
        """The passage nearest to these words (difflib over windows of as many words): {text, line, score}."""
        import difflib
        n, m = len(self.words), min(len(words), len(self.words))
        if not n or not m or n > 60_000:
            return None
        sm = difflib.SequenceMatcher(None, autojunk=False)
        sm.set_seq2(words)
        best, at = 0.0, 0
        for k in range(n - m + 1):
            sm.set_seq1(self.words[k:k + m])
            if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
                continue
            r = sm.ratio()
            if r > best:
                best, at = r, k
        if best < 0.3:
            return None
        s, e = self.cut(at, m)
        return {"text": self.text[s:e], "line": self.text.count("\n", 0, s) + 1, "score": round(best, 2)}


def find_quote(text: str, quote: str, T: _Text | None = None) -> dict:
    """One part's quote of a text -> {"ok": True, "text": the ORIGINAL words (pieces joined with " … "), "at":
    [[start, end], ...]} or {"ok": False, "why", "closest": {"text", "line", "score"} | None}. The words must be the
    text's words in its order, whole; pieces may be left out with ... ; case, accents, curly quotes, dashes,
    punctuation and markdown marks may differ - the saved quote is always the text's own."""
    T = T or _Text(text)
    q = str(quote or "").strip()
    if not q:
        return {"ok": False, "why": "empty", "closest": None}
    if len(q) > QUOTE_MAX:
        return {"ok": False, "why": f"{len(q)} characters, at most {QUOTE_MAX}: shorten it with ... (keep the words "
                                    f"that say this part)", "closest": None}
    qf = fold_map(q)[0]
    whole = _TOK.findall(qf)
    if not whole:
        return {"ok": False, "why": "no words in it", "closest": None}
    k = T.find(whole)
    if k >= 0:
        s, e = T.cut(k, len(whole), *_edges(qf))
        return {"ok": True, "text": T.text[s:e], "at": [[s, e]]}
    pieces = [p.strip() for p in re.split(r"\.{3,}", qf) if _TOK.search(p)]
    if len(pieces) < 2:
        return {"ok": False, "why": "not in the text", "closest": T.closest(whole)}
    at, pos = [], 0
    for p in pieces:
        w = _TOK.findall(p)
        if len("".join(w)) < PIECE_MIN:
            return {"ok": False, "why": f'the piece "{p}" is too short to check - quote a few words', "closest": None}
        k = T.find(w, pos)
        if k < 0:
            if T.find(w) >= 0:
                return {"ok": False, "why": f'"{_snip(p)}" comes earlier in the text than the piece before it - quote '
                                            f'the pieces in the text\'s order', "closest": None}
            return {"ok": False, "why": f'"{_snip(p)}" is not in the text', "closest": T.closest(w)}
        at.append(list(T.cut(k, len(w), *_edges(p))))
        pos = k + len(w)
    return {"ok": True, "text": " … ".join(T.text[s:e] for s, e in at), "at": at}


def _script_check(text: str) -> dict:
    from . import script as SC                          # script.py imports this module: only when it is needed
    return SC.check(text, I18N=SC.ENGLISH)              # Claude reads the problems it names: English


def _names(model: str, text: str, file: str = "") -> bool:
    """Does the text (or the name of the file it came from) name this model? ("Kling Image 3.0" <- KLING_3.0_Guide)"""
    have = set(_toks(text)) | set(_toks(re.sub(r"[_\-.]+", " ", Path(str(file or "")).stem)))
    need = [w for w in _toks(model) if len(w) >= 3 and not w.isdigit() and w not in _GENERIC_MODEL]
    return not need or any(w in have for w in need)


def verify_check(rec: dict, changes: dict, facts: dict | None = None, warnings: list | None = None,
                 who: str = "the text") -> tuple[dict, list[str]]:
    """Claude's check of one prompt / script (the changes for update(), or a new record's fields for import) ->
    (the clean changes, problems). Any problem = save nothing; each names the part and, for a quote it cannot find,
    the closest real passage. rec = the saved record (for an import: its kind, text and source). The rules:
      A. every quoted part is in THIS text: its whole words in its order, pieces left out with ..., at most
         QUOTE_MAX characters - the saved text becomes the text's ORIGINAL words, `at` = their [start, end]
      B. "missing" quotes nothing; "clear" / "vague" quote the text
      C. the parts are the kind's (SLOTS), each once; another one needs "extra": true and a "why"
      D. every part of the kind is a row, or in "skipped" with why it is not part of this prompt
      E. a script / hook: a part the measured script check flags (warn / bad) is not "clear" without "overrides":
         {part: why the rule does not apply} (kept on the row as "override")
      F. words in double quotes in review.why are the text's (a new line belongs in tip / fix: not checked)
      G. a model neither the text nor its file names is left out (a prompt Claude wrote keeps the model asked for)
    B, D and E apply to a check (rows with a status); a plain split (no status anywhere) gets A and C. Soft
    warnings (5 stars with 2+ parts missing, a hook pattern the measured check disagrees with, a long title or one
    that starts "Prompt for") go to `warnings`. A title record is Claude's own words (its text is written from its
    fields): returned as it is. facts = a text set's measured facts ("script" = its script check)."""
    W = warnings if warnings is not None else []
    kind = rec.get("kind") or changes.get("kind")
    clean = {k: v for k, v in changes.items() if k != "overrides"}
    if kind == "title":
        return clean, []
    text = str(rec.get("text") or "")
    T = _Text(text)
    P: list[str] = []
    slots = SLOTS.get(kind, [])
    rows: list[dict] = []
    sk = changes.get("skipped") or {}
    ov = changes.get("overrides") or {}
    if not isinstance(sk, dict):
        P.append('skipped = {"part": "why it is not part of this prompt"}')
        sk = {}
    if not isinstance(ov, dict):
        P.append('overrides = {"part": "why the measured check does not apply"}')
        ov = {}
    st = changes.get("structure")
    if st is not None:
        if not isinstance(st, list):
            P.append("structure = a list of {slot, text, status, tip}")
            st = []
        checked = any(isinstance(x, dict) and x.get("status") for x in st)
        seen: set = set()
        for i, x in enumerate(st, 1):
            if not isinstance(x, dict) or not str(x.get("slot") or "").strip():
                P.append(f"row {i}: each row names its part (slot)")
                continue
            slot = str(x["slot"]).strip()
            if slot in seen:
                P.append(f"{slot}: two rows - one row per part")
                continue
            seen.add(slot)
            if slot not in slots and not (x.get("extra") and str(x.get("why") or "").strip()):
                P.append(f'{slot}: not a part of a {kind} ({", ".join(slots)}) - use one of them, or mark the row '
                         f'"extra": true with a "why"')
            row = {k: v for k, v in x.items() if k not in ("at", "override")}      # the tool writes those two
            row["slot"] = slot
            t, status = str(x.get("text") or "").strip(), x.get("status")
            if checked:
                if status not in STATUSES:
                    P.append(f"{slot}: status clear, vague or missing (got {status!r})")
                elif status == "missing" and t:
                    P.append(f'{slot}: "missing" but it quotes "{_snip(t)}" - a missing part quotes nothing ("")')
                elif status != "missing" and not t:
                    P.append(f'{slot}: "{status}" needs the words {who} says it with - or "missing" (not said, and '
                             f'it matters), or "skipped" with why it is not part of this {kind}')
            if t:
                q = find_quote(text, t, T)
                if q["ok"]:
                    row["text"], row["at"] = q["text"], q["at"]
                else:
                    c = q.get("closest")
                    P.append(f'{slot}: "{_snip(t)}" - {q["why"].replace("the text", who)}'
                             + (f'; closest: "{_snip(c["text"], 90)}" (line {c["line"]})' if c else ""))
            else:
                row["text"] = ""
            rows.append(row)
        if checked:
            for s in slots:
                if s not in seen and not str(sk.get(s) or "").strip():
                    P.append(f'{s}: no row - every part of a {kind} gets one (clear / vague / missing), or goes in '
                             f'"skipped" with why it is not part of this {kind}')
            if kind in SCRIPT_FLAGS:
                sc = (facts or {}).get("script") or _script_check(text)
                flags = {c["id"]: c for c in sc.get("checks") or [] if c.get("status") in ("warn", "bad")}
                for row in rows:
                    hit = [flags[c] for c in SCRIPT_FLAGS[kind].get(row["slot"], ()) if c in flags]
                    if not hit or row.get("status") != "clear":
                        continue
                    why = " ".join(str(ov.get(row["slot"]) or "").split())
                    if why:
                        row["override"] = why
                    else:
                        P.append(f'{row["slot"]}: "clear", but the measured check flags it ({hit[0]["label"]}: '
                                 f'{_snip(hit[0]["detail"], 120)}) - mark it vague / missing, or say why the rule '
                                 f'does not apply: "overrides": {{"{row["slot"]}": "..."}}')
                mp = (sc.get("hook") or {}).get("pattern")
                if changes.get("pattern") and mp and changes["pattern"] != mp:
                    W.append(f'pattern "{changes["pattern"]}" - the measured check reads the hook as "{mp}"')
        for s in ov:
            if s not in seen:
                P.append(f'overrides "{s}": no row with that part')
        clean["structure"] = rows
    for s, why in sk.items():
        if st is not None and s in {r["slot"] for r in rows}:
            P.append(f'{s}: a row and "skipped" - one of them')
        elif s not in slots:
            P.append(f'skipped "{s}": not a part of a {kind} ({", ".join(slots)})')
        elif not str(why or "").strip():
            P.append(f'skipped "{s}": say why it is not part of this {kind}')
    if "skipped" in changes or st is not None:           # a new check replaces the parts skipped before
        clean["skipped"] = {str(s): " ".join(str(w).split()) for s, w in sk.items()}
    rv = changes.get("review")
    if isinstance(rv, dict):
        for q in re.findall(r'[“"«]([^”"»\n]{3,400})[”"»]', str(rv.get("why") or "")):
            if not find_quote(text, q, T)["ok"]:
                P.append(f'review.why quotes "{_snip(q)}" - that is not in {who}: quote it exactly, or put a new line '
                         f'in "fix" (not checked)')
        if rv.get("stars") == 5 and sum(1 for x in rows if x.get("status") == "missing") >= 2:
            W.append("5 stars with 2 or more parts missing - is that right?")
    m = " ".join(str(changes.get("model") or "").split())
    src = rec.get("source") or {}
    if m and m != " ".join(str(rec.get("model") or "").split()) and src.get("type") != "written" \
            and not _names(m, text, src.get("file") or ""):
        W.append(f'model "{m}" - neither {who} nor its file names it: left out')
        clean.pop("model", None)
    tt = " ".join(str(changes.get("title") or "").split())
    if len(tt) > 80:
        W.append(f"the title has {len(tt)} characters - 3-6 words that say which one it is")
    if re.match(r"(?i)(prompt|guion|script)s?\s+(for|para)\b", tt):
        W.append('the title starts like "Prompt for ..." - say what it makes instead')
    return clean, P


def _lines_of(text: str) -> list[str]:
    """A text in the pieces verify_source finds one after another: its lines, cut at sentence ends."""
    out = []
    for ln in str(text or "").replace("\r", "").split("\n"):
        out += [s for s in re.split(r"(?<=[.!?…])\s+", ln) if _TOK.search(fold_map(s)[0])]
    return out


def verify_source(rec: dict, notes: list | None = None) -> list[str]:
    """A prompt Claude copied out of an attached file (source.file: *Let Claude sort it*, a text set's file to sort)
    must be in that file - every line / sentence of its text, in the file's order (a page number or a header between
    two is fine; punctuation, case and line breaks may differ). [] = fine, else the problems in words. A file
    MotionLab cannot read (a PDF without the PDF reader, a scan) is not checked: `notes` says so."""
    N = notes if notes is not None else []
    f = str((rec.get("source") or {}).get("file") or "").strip()
    if not f:
        return []
    p = FILES / Path(f).name
    if not p.is_file():
        return [f'source.file "{f}": no attached file with that name']
    try:
        hay = file_text(p)
    except ValueError as e:
        return [str(e)]
    if not hay.strip():
        N.append(f"{p.name}: MotionLab cannot read its text on this PC - this copy of it was not checked")
        return []
    T = _Text(re.sub(r"(\w)-\n(\w)", r"\1\2", hay))    # a word a PDF broke over two lines
    P, pos = [], 0
    for piece in _lines_of(rec.get("text") or ""):
        w = _toks(piece)
        k = T.find(w, pos)
        if k >= 0:
            pos = k + len(w)
            continue
        if T.find(w) >= 0:
            P.append(f'"{_snip(piece)}" comes earlier in {p.name} - keep the file\'s order (one prompt = one record)')
        else:
            c = T.closest(w)
            P.append(f'"{_snip(piece)}" is not in {p.name} - copy its words as they are (no translating, no cleaning '
                     f'up)' + (f'; closest: "{_snip(c["text"], 90)}" (line {c["line"]})' if c else ""))
        if len(P) >= 6:
            P.append("... and more like these")
            break
    return P


# what a prompt names and needs, measured (a text set's facts) - the twins of app.js TOOLS / ptool / pneeds: keep the
# two lists alike
TOOLS_RX = re.compile(r"higgsfield|invideo|kling|runway|pika|luma|hailuo|minimax|sora|veo|midjourney|nano ?banana|"
                      r"gpt[- ]?image|chatgpt|dall-?e|seedance|flux|leonardo|ideogram|krea|capcut|hedra|heygen|"
                      r"elevenlabs|suno|wan ?2", re.I)


def tool_named(r: dict) -> str:
    """The site or app the prompt runs on (its model, else one the text names), "" for scripts / hooks / briefs."""
    model, kind, text = str(r.get("model") or ""), r.get("kind"), str(r.get("text") or "")
    if model and TOOLS_RX.search(model):
        return model
    if kind not in ("shot", "image"):
        return ""
    if model:
        return model
    m = TOOLS_RX.search(text)
    return m[0][0].upper() + m[0][1:] if m else ("an AI video tool" if kind == "shot" else "an AI image tool")


def needs(r: dict) -> list[str]:
    """What the user brings: your clips (a brief), you on camera (a script / hook), your clip / your photo / text only."""
    kind, t = r.get("kind"), str(r.get("text") or "")
    if kind == "brief":
        return ["your clips"]
    if kind in ("script", "hook"):
        return ["you on camera"]
    if kind == "title":
        return ["shots to film"]
    both = t + " " + next((str(x.get("text") or "") for x in r.get("structure") or [] if x.get("slot") == "references"), "")
    if re.search(r"@video\d*|source clip|tripod clip|your (clip|video|footage)|upload(ed)? (a |your )?(clip|video)|"
                 r"video[- ]to[- ]video", both, re.I):
        return ["your clip"]
    if re.search(r"@image\d*|reference (image|photo|picture)|your (photo|picture|selfie)|upload(ed)? (a |your )?"
                 r"(photo|image|picture)|image[- ]to[- ]video|start frame", both, re.I):
        return ["your photo"]
    return ["text only"]


def kind_evidence(text: str) -> dict:
    """guess_kind's reasons (a text set shows them next to the kind): {"kind", "why"} = the words it counted."""
    t = str(text or "")
    k = guess_kind(t)
    parts = []
    for label, rx in (("movement / video words", _MOTION), ("camera / light words", _LOOK),
                      ("still-picture words", _STILL), ("editing words", _BRIEF), ("said to a viewer", _SPOKEN)):
        hit = [m.group(0).lower() for m in rx.finditer(t)]
        if hit:
            one = list(dict.fromkeys(hit))
            parts.append(f"{label} ×{len(hit)} ({', '.join(one[:4])}{'…' if len(one) > 4 else ''})")
    if k in ("hook", "script"):
        n = len(t.split())
        parts.append(f"{n} words ({'up to 40: a hook' if k == 'hook' else 'over 40: a script'})")
    return {"kind": k, "why": "; ".join(parts) or "no tell-tale words"}


# words that NAME a part of a shot / image prompt - evidence for Claude's check (where to look), never a refusal
SLOT_WORDS = {
    "references": r"@(?:image|video|img)\s?\d*|\breference (?:image|photo|picture|video)s?\b|\buploaded?\b",
    "camera": r"\b(?:dolly(?:[- ](?:in|out|zoom))?|pans?|panning|tilts?|tilting|tracking(?: shot)?|handheld|drone|"
              r"orbit(?:s|ing)?|crane|push[- ]in|pull[- ](?:back|out)|whip[- ]pan|static|locked[- ]off|fpv|pov|"
              r"close[- ]?ups?|wide shot|medium shot|over[- ]the[- ]shoulder)\b",
    "lens": r"\b(?:\d{2,3}\s?mm|anamorphic|wide[- ]angle|telephoto|macro|fisheye|depth of field|bokeh)\b",
    "light": r"\b(?:backlit|rim light|golden hour|blue hour|neon|soft light|hard light|low[- ]key|high[- ]key|lighting|"
             r"shadows?|sunset|sunrise|lamp|candle ?light)\b",
    "motion": r"\b(?:slow[- ]motion|slow-mo|speed ramp|time[- ]?lapse|motion blur|\d+\s?fps)\b",
    "audio": r"\b(?:audio|sound|music|sfx|voice ?over|dialogue|silen(?:t|ce)|ambient)\b",
    "length / aspect": r"\b\d+(?:\.\d+)?\s?(?:s|sec|secs|seconds)\b|\b(?:9:16|16:9|1:1|4:5|21:9)\b|\bvertical\b|"
                       r"\bhorizontal\b",
    "avoid": r"\b(?:avoid|without|don'?t|do not|never|no (?:text|logos?|watermarks?|extra \w+))\b",
}
_SLOT_RX = {k: re.compile(v, re.I) for k, v in SLOT_WORDS.items()}


def slot_words(text: str, kind: str) -> dict:
    """{part: [[words, start, end], ...]} for a shot / image prompt (up to 6 a part) - evidence only."""
    if kind not in ("shot", "image"):
        return {}
    out = {}
    for slot in SLOTS[kind]:
        rx = _SLOT_RX.get(slot)
        hits = [[m.group(0), m.start(), m.end()] for m in rx.finditer(text or "")][:6] if rx else []
        if hits:
            out[slot] = hits
    return out


def overview() -> dict:
    """What the app's prompt library shows."""
    items = load_all()
    for r in items:                                     # older prompts saved without a title (Claude's check adds one)
        if not r.get("title"):
            r["title_auto"] = auto_title(r.get("text", ""), r.get("kind", ""))
        r["created"] = created(r)                       # the app's NEW badge (a reused id is a new card: id + time)
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
    if r.get("kind") == "title":
        L += describe_title(r)
    if r.get("structure") and full and any(x.get("status") for x in r["structure"]):
        st, vd = r["structure"], r.get("verdicts") or {}
        quoted = [x for x in st if str(x.get("text") or "").strip()]
        how = ("" if not quoted else "quotes found in the text" if all(x.get("at") for x in quoted)
               else "quotes not verified - checked before MotionLab checked quotes; check it again")
        L.append("  Claude's check (part: status - what it says - tip" + (f"; {how}" if how else "") + "):")  # 0.3.4
        L += [f"    {x['slot']}: {x.get('status') or '-'} - {x['text'] or '(not said)'}"
              + (f" - tip: {x['tip']}" if x.get("tip") else "")
              + (f" - the measured check flags it; Claude: {x['override']}" if x.get("override") else "")
              + (f" - the user: {vd[x['slot']].upper()}" if vd.get(x["slot"]) else "") for x in st]
        if r.get("skipped"):                            # 2026-10-18: parts left out on purpose, with why
            L.append("  not part of this prompt: " + "; ".join(f"{k} ({v})" for k, v in r["skipped"].items()))
        other = {k: v for k, v in vd.items() if k not in {x["slot"] for x in st}}
        if other:
            L.append("  the user's verdicts on other parts: " + ", ".join(f"{k}: {v.upper()}" for k, v in other.items()))
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
    if r.get("kind") == "title" and (r.get("titles") or r.get("concepts")):
        return "\n".join(L)                             # its text = the lines above in other words
    L.append("  text: " + (text if full or len(text) <= 300 else text[:300] + " ..."))
    return "\n".join(L)
