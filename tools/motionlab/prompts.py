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
from pathlib import Path

from .util import LAB, read_json, write_json

FOLDER = "knowledge/local/prompts"                      # relative to the lab (the app's "Folder" button)
HOME = LAB / FOLDER
KINDS = {"shot": "Video-model shot", "image": "Image (still / start frame)", "hook": "Hook (first 3 s)",
         "script": "Talking script"}
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
}
HOOK_PATTERNS = ["question", "bold claim", "number", "story", "contrarian", "demo", "curiosity gap", "call-out"]
_LOCK = threading.RLock()


def _today() -> str:
    return _dt.date.today().isoformat()


def _path(pid: str) -> Path:
    m = re.fullmatch(r"(shot|image|hook|script)-(\d{3,})", str(pid))
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
            raise ValueError("structure = a list of {slot, text}")
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
    review {stars 0-5, why, fix}, workflow (name of a multi-step recipe) + step (1, 2, ...), notes (how to use it)."""
    r = {"kind": rec.get("kind"), "title": str(rec.get("title") or "").strip(), "text": str(rec.get("text") or "").strip(),
         "model": str(rec.get("model") or "").strip(), "source": dict(rec.get("source") or {}),
         "result": {"rating": None, "note": "", **(rec.get("result") or {})},
         "structure": rec.get("structure") or None, "pattern": rec.get("pattern") or "",
         "tags": list(rec.get("tags") or []), "made_from": list(rec.get("made_from") or []),
         "review": _review(rec.get("review")), "workflow": str(rec.get("workflow") or "").strip(),
         "step": rec.get("step"), "notes": str(rec.get("notes") or "").strip(),
         "added": _today(), "updated": _today()}
    _check(r)
    with _LOCK:
        r["id"] = next_id(r["kind"])
        write_json(_path(r["id"]), {"id": r["id"], **r}, indent=1)
    return get(r["id"])


def update(pid: str, **changes) -> dict:
    """Change fields of a saved prompt: title, model, structure, pattern, tags, workflow, step, notes, review (Claude's
    stars), rating + note (the user's) - the text and the source stay as they were added."""
    with _LOCK:
        r = get(pid)
        for k in ("title", "model", "structure", "pattern", "tags", "workflow", "step", "notes"):
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


def parse_paste(text: str) -> list[dict]:
    """The user's paste (TEMPLATE: blocks that start with 'PROMPT <n>', key: value lines, then 'text:' and the prompt
    until the next block) -> records for `add`. Raises ValueError naming the block that is wrong."""
    blocks = re.split(r"(?im)^\s*PROMPT\s*#?\s*\d*\s*:?\s*$", str(text).replace("\r", ""))
    out = []
    for n, b in enumerate([b for b in blocks if b.strip()], 1):
        m = re.search(r"(?im)^\s*(?:prompt )?text\s*:", b)
        if not m:
            raise ValueError(f"prompt {n}: no 'text:' line")
        head, body = b[:m.start()], b[m.end():]
        kv = {}
        for line in head.splitlines():
            m = re.match(r"\s*([a-z ]+?)\s*:\s*(.*)$", line, re.I)
            if m:
                kv[m[1].lower()] = m[2].strip()
        try:
            kind = kv.get("kind", "").lower().strip()
            kind = {"shots": "shot", "video": "shot", "images": "image", "photo": "image", "hooks": "hook",
                    "scripts": "script"}.get(kind, kind)
            rec = {"kind": kind, "title": kv.get("title", ""), "model": kv.get("model", "").strip(" -") or "",
                   "source": _source(kv.get("source", "")), "result": _result(kv.get("result", "")),
                   "text": body.strip(), "tags": [t.strip() for t in kv.get("tags", "").split(",") if t.strip()]}
            if rec["model"].lower() in ("none", "n/a"):
                rec["model"] = ""
            _check(rec)
        except ValueError as e:
            raise ValueError(f"prompt {n}: {e}") from None
        out.append(rec)
    if not out:
        raise ValueError("no prompts found - start each one with a line 'PROMPT 1', 'PROMPT 2', ...")
    return out


def import_paste(text: str) -> list[dict]:
    """Parse the whole paste first (nothing is saved when one block is wrong), then save every prompt."""
    return [add(r) for r in parse_paste(text)]


def overview() -> dict:
    """What the app's Prompts page shows."""
    items = load_all()
    return {"kinds": [{"id": k, "label": v, "count": sum(1 for r in items if r["kind"] == k),
                       "slots": SLOTS[k]} for k, v in KINDS.items()],
            "items": items, "template": TEMPLATE, "folder": FOLDER}


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
    if r.get("structure"):
        L.append("  structure: " + " > ".join(f"{x['slot']}: {x['text']}" for x in r["structure"]))
    elif full:
        L.append("  structure: not split yet")
    text = r.get("text", "")
    L.append("  text: " + (text if full or len(text) <= 300 else text[:300] + " ..."))
    return "\n".join(L)
