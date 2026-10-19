"""Text sets (2026-10-18, the Analyser's third way *Scripts & prompts*; the user: "it should also be able to analize
propmpts ... make sure it is able to handle batches or multiple at the same time, imagine i wanted to analize 10
prompts at the same time i could and it wouldnt allucinate"): up to MAX_ITEMS talking scripts, hooks, prompts for AI
video / image tools and briefs, checked together. Each text keeps its ONE home in the prompt library
(knowledge\\local\\prompts\\<kind>\\<id>.json - Claude's check card, wishes, Optimize, Film it, ratings and Style like
keep working on it); a text the library has already is re-used (the same words after folding = the same sha1). The
set is the batch around them - no .app\\batches file: its state is read from its own files. CLI: tools\\textsets.py.

Layout - one set per folder under ROOT (analysis\\texts\\; MOTIONLAB_TEXTS_ROOT or the CLI's --root moves it, tests do):
    <ROOT>\\<set>\\set.json      the lab's, written only here: {"name", "label", "created", "updated", "source": {"kind":
                                  paste|files|library, "type": tested|creator, "creator", "link", "files", "to_sort"
                                  (files MotionLab could not read - Claude sorts them in), "sorted"}, "items": [{"n",
                                  "id" (the prompt), "sha1", "kind", "kind_from" (guess|you|claude|library|changed),
                                  "kind_why", "from" ({"paste": k} | {"file", "part"} | {"library": true}), "facts"
                                  (measured, below), "check" (the stamp of a check that passed: {"sha1", "kind",
                                  "date", "quotes", "skipped", "overrides", "by"}), "gone" (deleted from the library)}],
                                  "summary"}
                  patterns.json     what the texts have in common: written ONLY by save_patterns() from Claude's draft -
                                  every example quote found in its own text, "how_many" counted here
                  verdicts.json     the user's: {"patterns": {"P1": {"v": correct|partly|wrong, "note", "date"}},
                                  "updated"} (the app; one home)
                  claude\\         Claude's drafts (item_<n>.json, patterns.json) - deleted once saved
<set> = util.safe_name of the name given. Item numbers never change (taking #3 out leaves a gap): the verdicts and
the patterns keep pointing at the right text.

Measured with no Claude (measure, milliseconds - inline, no job): per text its words, characters, language, the kind
guess with its reasons, the tool it names and what it needs, links and @image / @video references, words that name a
part of a shot / image (evidence only, never a refusal), exact and near duplicates, the analysed references a brief /
script names, and for scripts / hooks the whole measured script check (script.check); for the set the kinds, the
languages, word counts, tools, phrases of 4-8 words shared by 2+ texts (with their numbers), the scripts' hook
patterns / length / call to action at the end / greeting first, the user's ratings.

What makes it hold (no "trust me"): a text counts as checked only when its stamp's sha1 and kind match it now, and a
stamp is written only after prompts.verify_check() found every quote of Claude's check in THAT text (save_check, or
tools\\prompts.py annotate -> note_check); the saved quotes are the text's original words + their positions "at". A
pattern's examples are found in their own texts and counted here. state() is the only truth - for the app (the card,
the page, the live line) and for *Continue with Claude*. Other people's words stay on this PC: nothing here writes to
knowledge\\ except the prompt records themselves (local, never shared).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import statistics
import threading
import time
from collections import Counter
from pathlib import Path

from . import i18n as I18N
from . import prompts as PR
from . import script as SC
from .util import ANALYSIS, LAB, read_json, safe_name, write_json

ROOT = Path(os.environ.get("MOTIONLAB_TEXTS_ROOT") or (ANALYSIS / "texts"))
MAX_ITEMS = 20             # texts in one set (the user's example: 10); above 10 the skill splits the work across helpers
MIN_WORDS = 5              # a shorter text has nothing to check
MAX_CHARS = 100_000        # per text (Prepare's limit for a script)
KINDS = ("shot", "image", "hook", "script", "brief")     # titles stay in Prepare (Title & thumbnail first)
PATTERN_KINDS = ("hook", "structure", "wording", "camera", "look", "length", "cta", "voice", "format", "other")
NEAR = 0.8                 # near duplicates: their 5-word shingles overlap (Jaccard) at least this much
PROMPT = "/analyze-reference texts {}"
KIND_WORD = {"shot": "video prompt", "image": "image prompt", "hook": "hook", "script": "talking script",
             "brief": "brief"}
# the same kinds counted, in the app's language (the set page's *Measured by MotionLab*; KIND_WORD = memory.md's)
_KIND_N = {"shot": lambda n: I18N.tn(n, "{n} video prompt", "{n} video prompts"),
           "image": lambda n: I18N.tn(n, "{n} image prompt", "{n} image prompts"),
           "hook": lambda n: I18N.tn(n, "{n} hook", "{n} hooks"),
           "script": lambda n: I18N.tn(n, "{n} talking script", "{n} talking scripts"),
           "brief": lambda n: I18N.tn(n, "{n} brief", "{n} briefs")}
# a pattern's "what" is words; the count is the tool's ("8 of 10" typed by Claude is refused)
_COUNTED = re.compile(r"\b\d+\s*(?:of|/|out of|de|von)\s*\d+\b|\b\d+(?:[.,]\d+)?\s*%|\bpercent\b|\bpor ?ciento\b", re.I)
_STOP = set("""a an the and or but of to in on at for with from by is are was be it this that these those as into your
you my our their his her its not no so if then than very just el la los las un una unos unas y o de del al en con por
para que se su sus es lo le""".split())
_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_LOCK = threading.Lock()


# ------------------------------------------------------------------------------------------ small helpers
def rel(p) -> str:
    """Lab-relative path with forward slashes; the full path when outside the lab (tests)."""
    try:
        return Path(p).resolve().relative_to(LAB.resolve()).as_posix()
    except (ValueError, OSError):
        return Path(p).as_posix()


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def _pl(n: int, w: str) -> str:
    return f"{n} {w}{'' if n == 1 else 's'}"


def _nums(ns) -> str:
    return " ".join(f"#{n}" for n in ns)


def _first(text: str, n: int = 140) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def set_name(name: str) -> str:
    """The folder name for a set (letters, digits, _ - . only); refuses an empty one."""
    if not re.search(r"\w", str(name or ""), re.U):
        raise ValueError(I18N.t("give the set a short name, e.g. seedance_prompts"))
    return safe_name(str(name))


def set_dir(name: str) -> Path:
    return Path(ROOT) / set_name(name)


def _lock(name: str) -> threading.RLock:
    key = str(set_dir(name)).lower()
    with _LOCKS_LOCK:
        return _LOCKS.setdefault(key, threading.RLock())


def _load(name: str) -> dict | None:
    try:
        S = read_json(set_dir(name) / "set.json")
    except (OSError, ValueError):
        return None
    return S if isinstance(S, dict) else None


def _need(name: str) -> dict:
    S = _load(name)
    if S is None:
        raise FileNotFoundError(f"no text set called '{name}' (textsets.py list shows them)")
    S.setdefault("items", [])
    S.setdefault("source", {})
    S["name"] = set_dir(name).name
    return S


def _save(name: str, S: dict) -> None:
    S["updated"] = _now()
    write_json(set_dir(name) / "set.json", S, indent=1)


def _get(pid) -> dict | None:
    try:
        return PR.get(str(pid))
    except (ValueError, OSError):
        return None


def _library() -> dict[str, dict]:
    """The prompt library by the sha1 of each text's folded words (the kinds a set can hold)."""
    out: dict[str, dict] = {}
    for r in PR.load_all():
        if r.get("kind") in KINDS and str(r.get("text") or "").strip():
            out.setdefault(PR.text_sha(r["text"]), r)
    return out


def known(text: str) -> dict | None:
    """The prompt the library already has with these words (folded), or None."""
    return _library().get(PR.text_sha(text))


def _source(s) -> dict:
    """Whose the texts are (the add dialog's question): tested = the user's own; creator = someone else's (a name
    and / or a link; "found somewhere" = a creator with no name)."""
    s = s if isinstance(s, dict) else {}
    t = str(s.get("type") or "tested")
    if t == "found":
        t, s = "creator", {}
    if t not in ("tested", "creator"):
        raise ValueError("whose are they: tested (yours) or creator (someone else's)")
    if t == "tested":
        return {"type": "tested"}
    link = str(s.get("link") or "").strip()[:500]
    if link and not re.match(r"https?://\S+$", link):
        raise ValueError(I18N.t("the creator's link starts with http:// or https://"))
    return {"type": "creator", "creator": " ".join(str(s.get("creator") or "").split())[:120], "link": link}


def source_of(name: str) -> dict:
    """The set's "whose" (for a text Claude sorts in from one of its files)."""
    return {k: v for k, v in (_need(name).get("source") or {}).items() if k in ("type", "creator", "link")} \
        or {"type": "tested"}


def _attached(f) -> Path:
    """A file the add dialog attached (POST /api/prompts/file -> knowledge\\local\\prompts\\files\\<name>)."""
    name = Path(str(f or "").replace("\\", "/")).name
    p = PR.FILES / name
    if not name or not p.is_file():
        raise ValueError(I18N.t("no attached file {name} - attach it again", name=repr(name or str(f))))
    return p


# ------------------------------------------------------------------------------------------ splitting (the preview)
def _pieces(text: str, source: dict | None = None) -> list[dict]:
    """A paste -> its texts: lines of only --- between them, or the older PROMPT n blocks (their kind / model /
    source / result lines kept - prompts.parse_paste)."""
    text = str(text or "").replace("\r", "")
    if not text.strip():
        return []
    if PR._HEAD.search(text):
        return [{"text": r["text"], "kind": r["kind"], "model": r.get("model") or "", "source": r.get("source"),
                 "title": r.get("title") or "", "result": r.get("result")}
                for r in PR.parse_paste(text, source=source or None)]
    return [{"text": p.strip()} for p in re.split(r"(?m)^\s*-{3,}\s*$", text) if p.strip()]


def _split(text: str = "", files=(), kinds: dict | None = None, source: dict | None = None, into: str = "") -> dict:
    kinds = {str(k): v for k, v in (kinds or {}).items() if v}
    lib = _library()
    have: dict[str, int] = {}
    room = MAX_ITEMS
    if into:
        S = _need(into)
        have = {it["sha1"]: it["n"] for it in S["items"] if not it.get("gone")}
        room = MAX_ITEMS - len(have)
    raw = [(x, {"paste": k}) for k, x in enumerate(_pieces(text, source), 1)]
    unread = []
    for f in files or []:
        p = _attached(f)
        try:
            t = PR.file_text(p)
        except ValueError as e:
            unread.append({"file": p.name, "why": str(e)})
            continue
        if not t.strip():
            unread.append({"file": p.name, "why": I18N.t("MotionLab cannot read its text on this PC - Claude reads it "
                                                         "and saves its scripts and prompts into the set")})
            continue
        parts = _pieces(t, source)
        raw += [(x, {"file": p.name, **({"part": k} if len(parts) > 1 else {})}) for k, x in enumerate(parts, 1)]
    items, seen = [], {}
    for i, (x, frm) in enumerate(raw, 1):
        t = x["text"]
        sha = PR.text_sha(t)
        lr = lib.get(sha)
        if lr:
            kind, kfrom, why = lr["kind"], "library", "the prompt library has these words already, with this kind"
        elif kinds.get(sha) in KINDS:
            kind, kfrom, why = kinds[sha], "you", "you picked it"
        else:
            ev = PR.kind_evidence(t)
            kind = x["kind"] if x.get("kind") in KINDS else ev["kind"] if ev["kind"] in KINDS else "script"
            kfrom, why = "guess", ev["why"]
        nw = len(t.split())
        problem = (I18N.t("too short to check - at least {n} words", n=MIN_WORDS) if nw < MIN_WORDS   # the page's
                   else I18N.t("too long - at most {n} characters", n=f"{MAX_CHARS:,}" if I18N.lang() == "en"
                               else I18N.num(MAX_CHARS)) if len(t) > MAX_CHARS else "")
        items.append({"i": i, "sha": sha, "preview": _first(t, 160), "words": nw, "chars": len(t), "kind": kind,
                      "kind_why": why, "kind_from": kfrom, "title": x.get("title") or PR.auto_title(t, kind),
                      "from": frm, "dup": f"#{seen[sha]}" if sha in seen else None,
                      "known": lr["id"] if lr else None, "in_set": f"#{have[sha]}" if sha in have else None,
                      "problem": problem, "_text": t, "_piece": x})
        seen.setdefault(sha, i)
    new = [x for x in items if not x["dup"] and not x["in_set"]]
    return {"items": items, "unread": unread, "new": len(new), "room": room, "too_many": len(new) > room,
            "max": MAX_ITEMS}


def split(text: str = "", files=(), kinds: dict | None = None, source: dict | None = None, into: str = "") -> dict:
    """The add dialog's numbered preview - nothing is written. -> {"items": [{"i", "sha", "preview", "words",
    "chars", "kind", "kind_why", "kind_from", "title", "from" ({"paste": k} | {"file", "part"}), "dup" ("#2": the
    same words earlier - added once), "known" (the library's prompt with these words: re-used), "in_set" (the set
    `into` has them as #n), "problem"}], "unread": [{"file", "why"}] (Claude reads them), "new", "room",
    "too_many", "max"}. kinds = {sha: kind} the user picked."""
    sp = _split(text, files, kinds, _source(source) if source else None, into)
    sp["items"] = [{k: v for k, v in x.items() if not k.startswith("_")} for x in sp["items"]]
    return sp


def _refuse(sp: dict) -> None:
    bad = [x for x in sp["items"] if x["problem"] and not x["dup"] and not x["in_set"]]
    if bad:
        raise ValueError("; ".join(f"#{x['i']}: {x['problem']}" for x in bad[:5]))
    if sp["too_many"]:
        raise ValueError(I18N.t("at most {max} in a set - {new} new here, room for {room}", max=sp["max"],
                                new=sp["new"], room=sp["room"]))


def _put(S: dict, sp: dict, src: dict, tags) -> tuple[int, int]:
    """The preview's new texts -> prompt records (all checked before any is saved) + the set's items."""
    plan = []
    for x in sp["items"]:
        if x["dup"] or x["in_set"]:
            continue
        if x["known"]:
            plan.append((x, None))
            continue
        piece = x["_piece"]
        s = dict(piece.get("source") or src)
        if x["from"].get("file"):
            s["file"] = x["from"]["file"]
        rec = {"kind": x["kind"], "text": x["_text"], "title": "", "model": piece.get("model") or "", "source": s,
               "tags": [str(t).strip().lower()[:40] for t in tags or [] if str(t).strip()][:12],
               "result": piece.get("result") or {}}
        PR._check({**rec, "result": {"rating": None, **(rec["result"] or {})}})
        plan.append((x, rec))
    n = max([it["n"] for it in S["items"]], default=0)
    added = reused = 0
    for x, rec in plan:
        if rec is None:
            r, reused = _get(x["known"]), reused + 1
        else:
            r, added = PR.add(rec), added + 1
        n += 1
        S["items"].append({"n": n, "id": r["id"], "sha1": x["sha"], "kind": r["kind"],
                           "kind_from": x["kind_from"], "kind_why": x["kind_why"], "from": x["from"], "facts": {}})
    return added, reused


def _unique(base: str) -> str:
    nm, k = base, 2
    while (Path(ROOT) / nm).exists():
        nm, k = f"{base}_{k}", k + 1
    return nm


def create(name: str = "", label: str = "", text: str = "", files=(), kinds: dict | None = None, source=None,
           tags=None) -> dict:
    """A new set (the add dialog, the CLI): everything is checked first - nothing is written when one text is wrong -
    then each new text is saved word for word in the prompt library (the "whose" the user picked + the file it came
    from), texts the library has already are re-used, all numbered #1..#N and measured -> set.json. A name in use
    gets _2, _3. -> {"set", "label", "added", "reused", "to_sort", "count", "command"}."""
    src = _source(source)
    sp = _split(text, files, kinds, src)
    _refuse(sp)
    if not sp["new"] and not sp["unread"]:
        raise ValueError(I18N.t("nothing to add - paste a script or a prompt, or attach a file"))
    first = next((x for x in sp["items"] if not x["dup"]), None)
    guess = (first["title"] if first else "") or (sp["unread"][0]["file"] if sp["unread"] else "")
    nm = _unique(set_name(name or label or guess))
    with _lock(nm):
        S = {"name": nm, "label": " ".join(str(label or name or guess or nm).split())[:80], "created": _now(),
             "updated": _now(), "source": {**src, "kind": "paste" if str(text or "").strip() else "files",
                                            "files": [_attached(f).name for f in files or []],
                                            "to_sort": [u["file"] for u in sp["unread"]], "sorted": []},
             "items": [], "summary": {}}
        added, reused = _put(S, sp, src, tags)
        _measure(S, _records(S))
        _save(nm, S)
    return {"set": nm, "label": S["label"], "added": added, "reused": reused, "to_sort": len(sp["unread"]),
            "count": len(S["items"]), "command": PROMPT.format(nm)}


def add_items(name: str, text: str = "", files=(), kinds: dict | None = None, source=None, tags=None) -> dict:
    """More texts into a set (the set page's *Add more*): the same rules; numbering goes on after the last #."""
    S0 = _need(name)
    src = _source(source) if source else {k: v for k, v in S0["source"].items() if k in ("type", "creator", "link")}
    sp = _split(text, files, kinds, src, into=name)
    _refuse(sp)
    if not sp["new"] and not sp["unread"]:
        raise ValueError(I18N.t("nothing new to add - those texts are in the set already"))
    with _lock(name):
        S = _need(name)
        added, reused = _put(S, sp, src, tags)
        s = S["source"]
        s["files"] = list(dict.fromkeys((s.get("files") or []) + [_attached(f).name for f in files or []]))
        s["to_sort"] = list(dict.fromkeys((s.get("to_sort") or []) + [u["file"] for u in sp["unread"]]))
        _measure(S, _records(S))
        _save(name, S)
    return {"set": S["name"], "label": S.get("label") or S["name"], "added": added, "reused": reused,
            "to_sort": len(sp["unread"]), "count": len(S["items"]), "command": PROMPT.format(S["name"])}


def room(name: str, n: int) -> None:
    """Refuses (ValueError) when n more texts would not fit in the set."""
    S = _need(name)
    have = sum(1 for it in S["items"] if not it.get("gone"))
    if have + n > MAX_ITEMS:
        raise ValueError(f"the set has {have} texts - room for {MAX_ITEMS - have} more, not {n}")


def add_records(name: str, ids: list[str], files=()) -> dict:
    """Prompts already in the library -> the set (tools\\prompts.py import --set: the texts Claude copied out of a
    file the lab could not read); those files count as sorted. A text the set has already is skipped."""
    with _lock(name):
        S = _need(name)
        have = {it["sha1"] for it in S["items"] if not it.get("gone")}
        n, added = max([it["n"] for it in S["items"]], default=0), 0
        for pid in dict.fromkeys(ids):
            r = _get(pid)
            if not r:
                raise ValueError(f"no prompt {pid}")
            sha = PR.text_sha(r.get("text") or "")
            if sha in have:
                continue
            have.add(sha)
            n += 1
            added += 1
            f = (r.get("source") or {}).get("file") or ""
            S["items"].append({"n": n, "id": r["id"], "sha1": sha, "kind": r["kind"], "kind_from": "claude",
                               "kind_why": "Claude sorted it in from the file", "from": {"file": f} if f else
                               {"library": True}, "facts": {}})
        s = S["source"]
        files = [Path(str(f)).name for f in files or [] if f]
        s["sorted"] = list(dict.fromkeys((s.get("sorted") or []) + files))
        s["to_sort"] = [f for f in s.get("to_sort") or [] if f not in files]
        if sum(1 for it in S["items"] if not it.get("gone")) > MAX_ITEMS:
            raise ValueError(f"at most {MAX_ITEMS} in a set")
        _measure(S, _records(S))
        _save(name, S)
    st = state(name)
    return {"added": added, "line": f"text set {S['name']}: {_pl(added, 'text')} added"
                                    + (f" from {', '.join(files)}" if files else "")
                                    + f" - {st['items']} in the set, {st['checked']} checked by Claude"}


def remove_item(name: str, n: int) -> dict:
    """#n out of the set; its prompt stays in the library and nothing is renumbered."""
    with _lock(name):
        S = _need(name)
        before = len(S["items"])
        S["items"] = [it for it in S["items"] if it["n"] != int(n)]
        if len(S["items"]) == before:
            raise ValueError(I18N.t("the set has no #{n}", n=n))
        _measure(S, _records(S))
        _save(name, S)
    return {"removed": int(n), "count": len(S["items"])}


# ------------------------------------------------------------------------------------------ the members, found
def _records(S: dict) -> dict[str, dict]:
    out = {}
    for it in S["items"]:
        r = _get(it.get("id"))
        if r:
            out[r["id"]] = r
    return out


def resolve(name: str) -> tuple[dict, dict]:
    """(set.json, {prompt id: record}) with every member found: a prompt whose id is gone (a kind change gives a new
    id - prompts.set_kind) is found again by its words (sha1); one deleted from the library is marked "gone".
    Writes set.json when something moved."""
    with _lock(name):
        S = _need(name)
        recs: dict[str, dict] = {}
        lib = None
        moved = False
        for it in S["items"]:
            r = _get(it.get("id"))
            if r is None or PR.text_sha(r.get("text") or "") != it["sha1"]:
                lib = _library() if lib is None else lib
                r = lib.get(it["sha1"])
                if r:
                    if r["kind"] != it.get("kind"):
                        it.update(kind_from="changed", kind_why="its kind was changed in the prompt library")
                    it.update(id=r["id"], kind=r["kind"])
                    it.pop("gone", None)
                    moved = True
                elif not it.get("gone"):
                    it["gone"] = True
                    moved = True
            if r:
                recs[r["id"]] = r
        if moved:
            _measure(S, recs)
            _save(name, S)
    return S, recs


def _checked(it: dict, r: dict | None) -> bool:
    """A text counts as checked only when its stamp (written when Claude's check passed) has its words and its kind
    now, and the record still holds a check."""
    c = it.get("check") or {}
    return bool(r and c and c.get("sha1") == it["sha1"] and c.get("kind") == r.get("kind")
                and any(x.get("status") for x in r.get("structure") or []))


def _items_sha(live: list[dict]) -> str:
    key = json.dumps(sorted([it["n"], it["sha1"], it["kind"]] for it in live))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def load_patterns(name: str) -> dict | None:
    try:
        p = read_json(set_dir(name) / "patterns.json")
    except (OSError, ValueError):
        return None
    return p if isinstance(p, dict) else None


def load_verdicts(name: str) -> dict:
    """The user's verdicts on the patterns: {"P1": {"v", "note", "date"}}."""
    try:
        v = read_json(set_dir(name) / "verdicts.json")
    except (OSError, ValueError):
        return {}
    return (v or {}).get("patterns") or {} if isinstance(v, dict) else {}


def save_verdicts(name: str, patterns: dict) -> dict:
    """The user's verdict on each pattern Claude named: correct / partly / wrong (+ a note); empty = removed."""
    with _lock(name):
        _need(name)
        cur = load_verdicts(name)
        for pid, x in (patterns or {}).items():
            if not re.fullmatch(r"P\d{1,3}", str(pid)):
                raise ValueError(f"not a pattern: {pid!r}")
            x = x if isinstance(x, dict) else {}
            v = str(x.get("v") or "")
            note = " ".join(str(x.get("note") or "").split())[:500]
            if v not in ("", *PR.VERDICTS):
                raise ValueError(f"a verdict is correct, partly or wrong - not {v!r}")
            if v or note:
                cur[str(pid)] = {"v": v, "note": note, "date": _now()}
            else:
                cur.pop(str(pid), None)
        write_json(set_dir(name) / "verdicts.json", {"patterns": cur, "updated": _now()}, indent=1)
    return {"patterns": cur}


def state(name: str, S: dict | None = None, recs: dict | None = None) -> dict:
    """The set's progress, read from its files: {"items", "checked", "left" [n], "stale" [n] (checked as another
    kind), "disputed" [n] (the user marked a part of Claude's check wrong / partly), "gone" [n], "to_sort" [files],
    "patterns": none | ok | stale, "done", "next" (in words), "prompt" (the Claude command)}."""
    if S is None or recs is None:
        S, recs = resolve(name)
    live = [it for it in S["items"] if not it.get("gone")]
    checked = [it["n"] for it in live if _checked(it, recs.get(it["id"]))]
    left = [it["n"] for it in live if it["n"] not in checked]
    stale = [it["n"] for it in live if it.get("check") and it["n"] not in checked]
    disputed = [it["n"] for it in live if any(v in ("wrong", "partly") for v in
                                              ((recs.get(it["id"]) or {}).get("verdicts") or {}).values())]
    pats = load_patterns(S["name"])
    pst = "none" if not pats else "ok" if pats.get("items_sha") == _items_sha(live) else "stale"
    to_sort = list(S["source"].get("to_sort") or [])
    need_p = len(live) >= 3
    done = bool(live) and not left and not to_sort and (not need_p or pst == "ok")
    nxt = (f"sort {_pl(len(to_sort), 'file')} into the set ({', '.join(to_sort)})" if to_sort
           else f"check {_nums(left)} ({len(left)} left)" if left
           else "find what they have in common" if need_p and pst != "ok"
           else f"re-check {_nums(disputed)} with the user's verdicts" if disputed else "done")
    return {"items": len(live), "checked": len(checked), "left": left, "stale": stale, "disputed": disputed,
            "gone": [it["n"] for it in S["items"] if it.get("gone")], "to_sort": to_sort, "patterns": pst,
            "done": done, "next": nxt, "prompt": PROMPT.format(S["name"])}


def _digest(r: dict) -> dict:
    st = r.get("structure") or []
    c = Counter(x.get("status") for x in st if x.get("status"))
    quoted = [x for x in st if str(x.get("text") or "").strip()]
    src = r.get("source") or {}
    return {"title": r.get("title") or PR.auto_title(r.get("text", ""), r.get("kind", "")), "kind": r.get("kind"),
            "stars": (r.get("review") or {}).get("stars"), "counts": {k: c.get(k, 0) for k in PR.STATUSES},
            "checked": bool(c), "verified": bool(quoted) and all(x.get("at") for x in quoted),
            "skipped": len(r.get("skipped") or {}), "rating": (r.get("result") or {}).get("rating"),
            "verdicts": dict(Counter((r.get("verdicts") or {}).values())), "source": src.get("type"),
            "creator": src.get("creator") or ""}


def list_sets() -> list[dict]:
    """Every set, newest change first: name, label, count, checked, stale, to_sort, has_patterns, patterns (none /
    ok / stale), kinds {kind: n}, updated, first (the first words of #1), done, prompt (the Claude command)."""
    out = []
    root = Path(ROOT)
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not d.is_dir() or not (d / "set.json").is_file():
            continue
        try:
            S, recs = resolve(d.name)
        except (OSError, ValueError):
            continue
        st = state(d.name, S, recs)
        live = [it for it in S["items"] if not it.get("gone")]
        first = next((recs[it["id"]]["text"] for it in live if it["id"] in recs), "")
        out.append({"name": S["name"], "label": S.get("label") or S["name"], "count": st["items"],
                    "checked": st["checked"], "stale": len(st["stale"]), "to_sort": len(st["to_sort"]),
                    "has_patterns": st["patterns"] != "none", "patterns": st["patterns"],
                    "kinds": dict(Counter(it["kind"] for it in live)), "updated": S.get("updated"),
                    "first": _first(first, 140), "done": st["done"], "prompt": st["prompt"]})
    return sorted(out, key=lambda s: s["updated"] or "", reverse=True)


def get_set(name: str) -> dict:
    """set.json + each item's text, "rec" (its prompt record in short: title, kind, stars, the counts of Claude's
    check, verified, skipped, the user's rating and verdicts), "checked" / "stale"; the patterns (or None), the
    user's verdicts on them, "state", "lines" (what MotionLab measured, in words) and "dir"."""
    S, recs = resolve(name)
    st = state(S["name"], S, recs)
    items = []
    for it in S["items"]:
        r = recs.get(it["id"])
        items.append({**it, "text": (r or {}).get("text", ""), "rec": _digest(r) if r else None,
                      "checked": not it.get("gone") and it["n"] not in st["left"], "stale": it["n"] in st["stale"]})
    return {**S, "items": items, "dir": rel(set_dir(S["name"])), "patterns": load_patterns(S["name"]),
            "verdicts": load_verdicts(S["name"]), "state": st, "lines": measured_lines(S)}


# ------------------------------------------------------------------------------------------ measured, no Claude
def _styles() -> list[dict]:
    try:
        return PR.all_styles()
    except Exception:                                    # noqa: BLE001 - the references are a nice-to-have fact
        return []


def _facts(r: dict, styles) -> dict:
    t = str(r.get("text") or "")
    f = {"words": len(t.split()), "chars": len(t), "lang": SC._lang(SC._words(t)), "title": PR.auto_title(t, r["kind"]),
         "tool": PR.tool_named(r), "needs": PR.needs(r), "links": re.findall(r"https?://\S+", t)[:10],
         "at_refs": sorted(set(m.lower().replace(" ", "") for m in re.findall(r"@(?:image|video|img)\s?\d*", t, re.I)))[:10],
         "words_found": PR.slot_words(t, r["kind"])}
    if r["kind"] in PR.STYLE_KINDS:
        styles = styles() if callable(styles) else styles
        f["refs"] = [x["name"] for x in PR.suggest_refs(t, styles)] if styles else []
    if r["kind"] in ("script", "hook"):
        f["script"] = SC.check(t, I18N=SC.ENGLISH)        # stored in set.json: English (Claude reads the facts)
    return f


def _shingles(words: list[str], k: int = 5) -> set:
    return {tuple(words[i:i + k]) for i in range(len(words) - k + 1)}


def _phrases(texts: dict[int, "PR._Text"], top: int = 12) -> list[dict]:
    """Phrases of 4-8 words that 2+ texts share (folded words), with the texts' numbers."""
    grams: dict[tuple, set] = {}
    for n, T in texts.items():
        for k in range(len(T.words) - 3):
            grams.setdefault(tuple(T.words[k:k + 4]), set()).add(n)
    shared = {g: s for g, s in grams.items()
              if len(s) >= 2 and sum(1 for w in g if len(w) >= 4 and w not in _STOP) >= 2}
    found: dict[str, dict] = {}
    for n, T in texts.items():
        W, k = T.words, 0
        while k < len(W) - 3:
            g = tuple(W[k:k + 4])
            if g not in shared:
                k += 1
                continue
            s, j = set(shared[g]), k
            while j + 1 <= len(W) - 4 and j + 1 - k + 4 <= 8:
                nxt = shared.get(tuple(W[j + 1:j + 5]))
                if not nxt or len(s & nxt) < 2:
                    break
                s &= nxt
                j += 1
            m = j - k + 4
            key = " ".join(W[k:k + m])
            if key not in found or len(s) > len(found[key]["items"]):
                a, b = T.cut(k, m)
                found[key] = {"text": T.text[a:b], "items": sorted(s), "words": m, "_key": key}
            k = j + 1
    keep: list[dict] = []
    for x in sorted(found.values(), key=lambda x: (-len(x["items"]), -x["words"])):
        if any(set(x["items"]) <= set(y["items"]) and x["_key"] in y["_key"] for y in keep):
            continue
        keep.append(x)
    return [{k: v for k, v in x.items() if k != "_key"} for x in keep[:top]]


def _measure(S: dict, recs: dict) -> None:
    """Every text's facts + the set's summary, into S (the caller saves)."""
    cache: list = []

    def styles():                                        # the analysed references: only when a brief / script needs them
        if not cache:
            cache.append(_styles())
        return cache[0]
    live = [it for it in S["items"] if not it.get("gone") and it.get("id") in recs]
    texts = {}
    for it in live:
        r = recs[it["id"]]
        it["facts"] = _facts(r, styles)
        if it.get("kind_from") == "guess":
            it["kind_why"] = PR.kind_evidence(r["text"])["why"]
        texts[it["n"]] = PR._Text(r["text"])
    sh = {n: _shingles(T.words) for n, T in texts.items()}
    near, dups = [], []
    ns = sorted(texts)
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            ia, ib = next(x for x in live if x["n"] == a), next(x for x in live if x["n"] == b)
            if ia["sha1"] == ib["sha1"]:
                dups.append([a, b])
            elif sh[a] and sh[b]:
                j = len(sh[a] & sh[b]) / len(sh[a] | sh[b])
                if j >= NEAR:
                    near.append([a, b, round(j, 2)])
    for it in live:
        it["facts"]["dup_of"] = next((a for a, b in dups if b == it["n"]), None)
        it["facts"]["near"] = sorted({b for a, b, _ in near if a == it["n"]} | {a for a, b, _ in near if b == it["n"]})
    words = [it["facts"]["words"] for it in live]
    langs = Counter(it["facts"]["lang"] or "?" for it in live)
    sc = [it["facts"]["script"] for it in live if it["facts"].get("script")]
    talks = [it["facts"]["script"] for it in live if it["facts"].get("script") and it["kind"] == "script"]
    rated = {k: [it["n"] for it in live if ((recs[it["id"]].get("result") or {}).get("rating")) == k]
             for k in ("good", "ok", "bad")}
    summ = {"n": len(live), "kinds": dict(Counter(it["kind"] for it in live)), "langs": dict(langs),
            "words": {"median": round(statistics.median(words)) if words else 0, "min": min(words, default=0),
                      "max": max(words, default=0)},
            "tools": dict(Counter(it["facts"]["tool"] for it in live                 # a tool named, not "an AI video tool"
                                  if it["facts"]["tool"] and not it["facts"]["tool"].startswith("an AI "))),
            "needs": dict(Counter(x for it in live for x in it["facts"]["needs"])),
            "phrases": _phrases(texts), "dups": dups, "near": near, "rated": rated, "made": _now()}
    if sc:
        secs = [s["seconds"] for s in sc if s.get("seconds")]
        summ["script"] = {"n": len(sc), "hook_patterns": dict(Counter((s.get("hook") or {}).get("pattern") or "none"
                                                                      for s in sc)),
                          "median_s": round(statistics.median(secs), 1) if secs else None, "scripts": len(talks),
                          "cta_end": sum(1 for s in talks if any(c["id"] == "cta" and c["status"] == "ok"   # scripts only:
                                                                 for c in s.get("checks") or [])),     # a hook asks nothing
                          "greeting_first": sum(1 for s in sc if (s.get("hook") or {}).get("opener"))}
    S["summary"] = summ


def measure(name: str) -> dict:
    """Every text measured again + the set's summary -> set.json. Returns the summary."""
    with _lock(name):
        S = _need(name)
        _measure(S, _records(S))
        _save(name, S)
    return S["summary"]


def _pattern_word(k: str) -> str:
    """A hook pattern (script.check's) in the app's language; "none" = no pattern."""
    return I18N.t("none|hook pattern") if k == "none" else I18N.t(k)


def measured_lines(S: dict) -> list[str]:
    """What MotionLab measured, in plain lines (the page's *Measured by MotionLab*; no Claude in them) - in the app's
    language (summary_lines, for Claude: the CLI's English)."""
    s = S.get("summary") or {}
    if not s.get("n"):
        return [I18N.t("Nothing measured yet.")]
    kinds = ", ".join(_KIND_N[k](n) if k in _KIND_N else f"{n} {k}{'' if n == 1 else 's'}" for k, n in
                      sorted(s["kinds"].items(), key=lambda kv: -kv[1]))
    langs = ", ".join(f"{k} {n}" for k, n in s.get("langs", {}).items() if k != "?")
    w = s.get("words") or {}
    v = {"texts": I18N.tn(s["n"], "{n} text", "{n} texts"), "kinds": kinds, "median": I18N.num(w.get("median", 0)),
         "min": I18N.num(w.get("min", 0)), "max": I18N.num(w.get("max", 0))}
    L = [I18N.t("{texts}: {kinds} · languages {langs} · {median} words in the middle one (from {min} to {max}).",
                langs=langs, **v) if langs else
         I18N.t("{texts}: {kinds} · {median} words in the middle one (from {min} to {max}).", **v)]
    if s.get("tools"):
        L.append(I18N.t("Tools they name: {tools}.", tools=", ".join(f"{k} {n}" for k, n in s["tools"].items())))
    if s.get("needs"):                                   # prompts.needs' words (English in set.json)
        L.append(I18N.t("What they need: {needs}.", needs=", ".join(f"{I18N.t(k)} {n}" for k, n in s["needs"].items())))
    if s.get("phrases"):
        L.append(I18N.t("Words they share: {phrases}.", phrases="; ".join(f"“{p['text']}” ({_nums(p['items'])})"
                                                                         for p in s["phrases"][:6])))
    if s.get("dups") or s.get("near"):
        tw = ([I18N.t("#{a} = #{b} (the same words)", a=a, b=b) for a, b in s.get("dups") or []]
              + [I18N.t("#{a} ≈ #{b} ({pct} % the same)", a=a, b=b, pct=round(j * 100)) for a, b, j in s.get("near") or []])
        L.append(I18N.t("Twins: {twins} - they count once in a pattern.", twins="; ".join(tw)))
    sc = s.get("script")
    if sc:
        facts = [I18N.t("hooks {patterns}", patterns=", ".join(f"{_pattern_word(k)} {n}"
                                                               for k, n in sc["hook_patterns"].items()))]
        if sc.get("median_s"):
            facts.append(I18N.t("≈ {s} s in the middle one", s=I18N.num(SC.as_g(sc["median_s"]))))
        if sc.get("scripts"):
            facts.append(I18N.tn(sc["scripts"], "one call to action at the end in {k} of {n} scripts",
                                 "one call to action at the end in {k} of {n} scripts", k=sc["cta_end"]))
        facts.append(I18N.t("a greeting first in {k} of {n}", k=sc["greeting_first"], n=sc["n"]))
        L.append(I18N.t("Scripts and hooks ({n}): {facts}.", n=sc["n"], facts="; ".join(facts)))
    r = s.get("rated") or {}
    if any(r.values()):
        L.append(I18N.t("Your ratings: {ratings} (the good ones weigh more).",
                        ratings="; ".join(f"{I18N.t(k + '|rating')} {_nums(v)}" for k, v in r.items() if v)))
    return L


def summary_lines(name: str) -> list[str]:
    """The set for Claude in plain lines: what was measured, how far Claude's check got, the patterns with the
    user's verdicts."""
    S, recs = resolve(name)
    st = state(S["name"], S, recs)
    L = [f"Text set {S['name']} ({S.get('label') or S['name']}), measured {(S.get('summary') or {}).get('made', '?')}:"]
    L += ["  " + x for x in measured_lines(S)]
    L.append(f"  Claude's check: {st['checked']} of {st['items']} checked (every quote found in its text)"
             + (f"; left {_nums(st['left'])}" if st["left"] else "") + (f"; to sort: {', '.join(st['to_sort'])}"
                                                                       if st["to_sort"] else "")
             + (f"; the user disputes parts of {_nums(st['disputed'])}" if st["disputed"] else "") + ".")
    P, V = load_patterns(S["name"]), load_verdicts(S["name"])
    for p in (P or {}).get("patterns") or []:
        v = V.get(p["id"]) or {}
        L.append(f"  {p['id']} {p['kind']}: {p['what']} ({p['how_many']}, {_nums(e['n'] for e in p['examples'])})"
                 + (f" - the user: {v['v'].upper()}" + (f" ({v['note']})" if v.get("note") else "") if v.get("v")
                    else "") + (" [found before the set changed]" if st["patterns"] == "stale" else ""))
    return L


def memory_lines() -> list[str]:
    """A few plain lines per set for Claude's memory (memory.md): its label, how many texts of which kinds, the
    patterns the user marked correct / partly with their k of N (the ones marked wrong are left out)."""
    out = []
    for s in list_sets():
        P, V = load_patterns(s["name"]), load_verdicts(s["name"])
        kinds = ", ".join(f"{n} {KIND_WORD.get(k, k)}{'' if n == 1 else 's'}" for k, n in s["kinds"].items())
        good, unmarked = [], 0
        for p in (P or {}).get("patterns") or []:
            v = (V.get(p["id"]) or {}).get("v")
            if v in ("correct", "partly"):
                note = (V[p["id"]].get("note") or "").strip()
                good.append(f"{p['kind']}: {p['what']} ({p['how_many']}, the user: {v}" + (f" - {note}" if note else "")
                            + ")")
            elif not v:
                unmarked += 1
        out.append(f"- Scripts & prompts \"{s['label']}\" ({kinds}; Claude checked {s['checked']} of {s['count']})"
                   + (": " + "; ".join(good) if good else "")
                   + (f" (+ {_pl(unmarked, 'pattern')} the user has not marked yet)" if unmarked else ""))
    return out


# ------------------------------------------------------------------------------------------ one text, for Claude
def _item(S: dict, ref) -> dict:
    """An item by its number (3, "#3") or its prompt id (shot-024)."""
    s = str(ref).strip().lstrip("#")
    for it in S["items"]:
        if (s.isdigit() and it["n"] == int(s)) or it.get("id") == s:
            return it
    if s.isdigit():                                      # the page names a text by its number
        raise ValueError(I18N.t("the set {name} has no #{n}", name=S["name"], n=s))
    raise ValueError(f"{s} is not in the set {S['name']}")


def show(name: str, ref=None) -> list[str]:
    """One text, for Claude: #n of N, its prompt id, kind and why, sha1, what was measured (evidence), the parts of
    its kind, the script check, its twins and the words it shares, Claude's check so far + the user's verdicts on it,
    then the text with line numbers. Without ref: the set in lines + one line per text."""
    S, recs = resolve(name)
    st = state(S["name"], S, recs)
    if ref is None:
        L = summary_lines(S["name"])
        L.append(f"  next: {st['next']}")
        for it in S["items"]:
            r = recs.get(it["id"])
            d = _digest(r) if r else {}
            mark = ("gone (deleted from the prompt library)" if it.get("gone") else "checked" if it["n"] not in st["left"]
                    else "checked as another kind - check it again" if it["n"] in st["stale"] else "not checked")
            c = d.get("counts") or {}
            L.append(f"  #{it['n']:<3} {it['id']:<11} {it['kind']:<6} {mark}"
                     + (f" ✓{c.get('clear', 0)} ~{c.get('vague', 0)} ✗{c.get('missing', 0)}" if d.get("checked") else "")
                     + f" | {_first(d.get('title') or (r or {}).get('text', ''), 60)}")
        return L
    it = _item(S, ref)
    r = recs.get(it["id"])
    if not r:
        return [f"#{it['n']} of the set {S['name']} was deleted from the prompt library - take it out: textsets.py "
                f"remove-item {S['name']} {it['n']}"]
    f, src = it.get("facts") or {}, r.get("source") or {}
    who = {"tested": "the user's own", "written": "written by Claude"}.get(src.get("type"), "a creator's" + (
        f" ({src.get('creator')}{' ' + src['link'] if src.get('link') else ''})" if src.get("creator") or src.get("link")
        else " (found somewhere)"))
    kfrom = {"guess": "guessed", "you": "the user picked it", "claude": "Claude", "library": "from the prompt library",
             "changed": "changed in the library"}.get(it.get("kind_from"), it.get("kind_from") or "")
    fr = it.get("from") or {}
    where = (f"the paste, text {fr['paste']}" if "paste" in fr else f"the file {fr['file']}"
             + (f", part {fr['part']}" if fr.get("part") else "") if fr.get("file") else "the prompt library")
    meas = [f"{f.get('words', 0)} words, {f.get('chars', 0)} characters, language {f.get('lang') or '?'}",
            f"tool {f['tool']}" if f.get("tool") else "", f"needs {', '.join(f['needs'])}" if f.get("needs") else "",
            f"links {' '.join(f['links'])}" if f.get("links") else "", " ".join(f.get("at_refs") or []),
            f"analysed references it may mean: {', '.join(f['refs'])}" if f.get("refs") else ""]
    L = [f"Text set {S['name']} ({S.get('label')}) - #{it['n']} of {st['items']} · prompt {r['id']} · sha1 {it['sha1']}",
         f"kind: {r['kind']} ({kfrom}: {it.get('kind_why') or '-'})",
         f"from: {where} · whose: {who}" + (f" · model {r['model']}" if r.get("model") else ""),
         "measured: " + "; ".join(x for x in meas if x)]
    if f.get("words_found"):
        L.append("words that name a part (evidence where to look - never proof): " + "; ".join(
            f"{k}: " + ", ".join(f"\"{w}\" @{a}" for w, a, _ in v[:4]) for k, v in f["words_found"].items()))
    L.append(f"the parts of a {r['kind']} - each a row (clear / vague / missing), or in \"skipped\" with why it is not "
             f"part of this {r['kind']}: {', '.join(PR.SLOTS[r['kind']])}")
    if r["kind"] in PR.SCRIPT_FLAGS:
        L.append("  a part the check below flags (~ / ✗) is not \"clear\" unless \"overrides\" says why: "
                 + "; ".join(f"{k} <- {', '.join(v)}" for k, v in PR.SCRIPT_FLAGS[r["kind"]].items()))
    if f.get("dup_of") or f.get("near"):
        L.append("twins: " + ", ".join(([f"the same words as #{f['dup_of']}"] if f.get("dup_of") else [])
                                      + [f"nearly the same as #{n}" for n in f.get("near") or []]))
    sh = [p for p in (S.get("summary") or {}).get("phrases") or [] if it["n"] in p["items"]]
    if sh:
        L.append("words it shares with other texts of the set: " + "; ".join(f"“{p['text']}” ({_nums(p['items'])})"
                                                                         for p in sh[:6]))
    if f.get("script"):
        L.append("the script check (measured, no Claude): " + SC.text_report(f["script"]).replace("\n", "\n  "))
    d = PR.describe(r, full=True).split("\n")
    chk = [x for x in d if x.startswith(("  Claude's check", "    ", "  not part of", "  the user's verdicts",
                                         "  review:", "  what the user wants"))]
    L.append("Claude's check so far:" if chk else "Claude's check so far: none")
    L += chk
    if it["n"] in st["stale"]:
        L.append("  (it was checked as another kind - check it again as a " + r["kind"] + ")")
    L.append("the text (line numbers are for you - quote the words, never the numbers):")
    L += [f"  {i:>3}| {ln}" for i, ln in enumerate(str(r.get("text") or "").split("\n"), 1)]
    L.append(f"draft -> {rel(set_dir(S['name']) / 'claude' / ('item_' + str(it['n']) + '.json'))} = "
             + json.dumps({"set": S["name"], "n": it["n"], "id": r["id"], "sha1": it["sha1"]})[:-1]
             + ', "title": "", "pattern": "", "tags": [], "structure": [...], "skipped": {}, "overrides": {}, '
               '"review": {"stars": 0, "why": "", "fix": ""}}')
    L.append(f"then: .venv\\Scripts\\python tools\\textsets.py check {S['name']} {it['n']} <that file>")
    return L


def _stamp(r: dict, it: dict) -> dict:
    st = r.get("structure") or []
    return {"sha1": it["sha1"], "kind": r["kind"], "date": _now(),
            "quotes": sum(1 for x in st if str(x.get("text") or "").strip()), "skipped": len(r.get("skipped") or {}),
            "overrides": sum(1 for x in st if x.get("override")), "by": "claude"}


def save_check(name: str, ref, draft: dict) -> dict:
    """Claude's check of ONE text of the set -> its prompt record, only when it holds: the draft names this set and
    this text (n, and the sha1 show() printed), the text's kind now, and prompts.verify_check() finds every quote in
    THIS text (words from another text of the set are named as such). Then prompts.update() saves title, structure
    (the original words + at), skipped, review, pattern, tags, model, and set.json gets the stamp.
    -> {"n", "id", "quotes", "skipped", "checked", "count", "line", "warnings"}. Refused = ValueError listing every
    problem; nothing saved."""
    if not isinstance(draft, dict):
        raise ValueError("the draft is a JSON object")
    S, recs = resolve(name)
    it = _item(S, ref)
    n = it["n"]
    if draft.get("set") not in (None, "") and set_name(draft["set"]) != S["name"]:
        raise ValueError(f"the draft is for the set {draft['set']!r}, not {S['name']!r}")
    if draft.get("n") not in (None, "") and str(draft["n"]).lstrip("#") != str(n):
        raise ValueError(f"the draft is for #{draft['n']}, not #{n} - one text per draft")
    if str(draft.get("sha1") or "") != it["sha1"]:
        raise ValueError(f"#{n}: the draft's sha1 is {draft.get('sha1')!r}, #{n}'s is {it['sha1']} - show "
                         f"{S['name']} {n} prints it: copy it, and check THIS text")
    if it.get("gone"):
        raise ValueError(f"#{n} was deleted from the prompt library")
    rec = recs.get(it["id"])
    if draft.get("kind") and draft["kind"] != rec["kind"]:
        raise ValueError(f"#{n} is a {rec['kind']} - change its kind first: textsets.py kind {S['name']} {n} "
                         f"{draft['kind']} --why \"...\"")
    if draft.get("id") and draft["id"] != rec["id"]:
        raise ValueError(f"the draft names {draft['id']}, #{n} is {rec['id']} now (show {S['name']} {n})")
    ch = {k: draft[k] for k in ("title", "structure", "skipped", "overrides", "review", "pattern", "tags", "model")
          if draft.get(k) is not None}
    if not ch.get("structure"):
        raise ValueError("a check has its structure: one row per part (or the part in \"skipped\")")
    w: list[str] = []
    clean, P = PR.verify_check(rec, ch, facts=it.get("facts"), warnings=w, who=f"#{n}'s text")
    if not P and not any(x.get("status") for x in clean.get("structure") or []):
        P.append("a check marks each part clear, vague or missing")
    if P:
        hints = []
        for row in ch.get("structure") or []:                # words of another text of the set: the texts got mixed up
            t = str((row or {}).get("text") or "").strip() if isinstance(row, dict) else ""
            if t and not PR.find_quote(rec["text"], t)["ok"]:
                hit = next((o["n"] for o in S["items"] if o["n"] != n and o["id"] in recs
                            and PR.find_quote(recs[o["id"]]["text"], t)["ok"]), None)
                if hit:
                    hints.append(f"{row.get('slot')}: those words are #{hit}'s - one text at a time: check #{n} "
                                 f"from show {S['name']} {n}")
        raise ValueError(f"#{n} not saved - {_pl(len(P), 'problem')}:\n  " + "\n  ".join(P + hints))
    r = PR.update(rec["id"], **clean)
    stamp = _stamp(r, it)
    with _lock(name):                                    # read again right before writing: the app may have changed it
        S2 = _need(name)
        for x in S2["items"]:
            if x["n"] == n:
                x["check"] = stamp
        _save(name, S2)
    st = state(name)
    line = (f"saved #{n} {r['id']}: {_pl(stamp['quotes'], 'quote')} found in its text, {_pl(stamp['skipped'], 'part')} "
            f"skipped - {st['checked']} of {st['items']} checked")
    return {"n": n, "id": r["id"], "quotes": stamp["quotes"], "skipped": stamp["skipped"], "checked": st["checked"],
            "count": st["items"], "line": line, "warnings": w}


def note_check(rec: dict) -> list[str]:
    """A check saved through tools\\prompts.py annotate (verified there): every set that holds this text stamps it.
    Returns a line per set."""
    out = []
    if not any(x.get("status") for x in rec.get("structure") or []):
        return out
    sha = PR.text_sha(rec.get("text") or "")
    root = Path(ROOT)
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not (d / "set.json").is_file():
            continue
        with _lock(d.name):
            S = _load(d.name)
            if not S:
                continue
            hit = [x for x in S.get("items") or [] if x.get("sha1") == sha and not x.get("gone")]
            if not hit:
                continue
            for x in hit:
                x.update(id=rec["id"], kind=rec["kind"], check=_stamp(rec, x))
            _save(d.name, S)
        st = state(d.name)
        out.append(f"text set {S['name']}: {_nums(x['n'] for x in hit)} checked - {st['checked']} of {st['items']}")
    return out


def set_item_kind(name: str, n, kind: str, why: str = "", by: str = "claude") -> dict:
    """#n is another kind (a guess was wrong): its prompt gets the kind (a new id - prompts.set_kind), the set follows,
    its facts are measured again (the parts change); a check made for the old kind no longer counts."""
    if kind not in KINDS:
        raise ValueError(f"a text set's kinds: {', '.join(KINDS)} (got {kind!r})")
    why = " ".join(str(why or "").split())[:300]
    if by == "claude" and not why:
        raise ValueError('say why it is that kind: --why "..."')
    S, recs = resolve(name)
    it = _item(S, n)
    old = it["id"]
    r = PR.set_kind(old, kind)
    with _lock(name):
        S2 = _need(name)
        for x in S2["items"]:
            if x["n"] == it["n"]:
                x.update(id=r["id"], kind=kind, kind_from=by, kind_why=why or "you picked it")
        _measure(S2, _records(S2))
        _save(name, S2)
    return {"n": it["n"], "id": r["id"], "kind": kind,
            "line": f"#{it['n']} is a {kind} now ({old} -> {r['id']}): check it as a {kind}"}


def _fact(it: dict, path: str):
    """A measured fact by its dotted path ("script.hook.pattern", "lang", "tool", "kind")."""
    if path == "kind":
        return it.get("kind")
    v = it.get("facts") or {}
    for k in path.split("."):
        v = v.get(k) if isinstance(v, dict) else None
    return v


def save_patterns(name: str, draft: dict) -> dict:
    """What the texts have in common, from Claude's draft {"summary", "patterns": [{"id": "P1", "kind", "what",
    "examples": [{"n", "quote"}], "except": [n], "measure"?}]} -> patterns.json, only when every example is a text of
    the set and its quote is found in THAT text (saved as its original words + at), 2+ different texts show it
    (twins count once), no count is typed into "what", an exception is not an example. "how_many" (k of N) and
    "rated_good" are counted here. A "measure" pattern ("script.hook.pattern=question") takes its texts from the
    facts and refuses an example whose facts say otherwise."""
    if not isinstance(draft, dict):
        raise ValueError("the draft is a JSON object")
    S, recs = resolve(name)
    live = {it["n"]: it for it in S["items"] if not it.get("gone") and it["id"] in recs}
    if len(live) < 2:
        raise ValueError("what they have in common needs 2 texts at least")
    group = {}
    for a, b in [x[:2] for x in (S.get("summary") or {}).get("dups", []) + (S.get("summary") or {}).get("near", [])]:
        ga, gb = group.get(a, a), group.get(b, b)
        for k, v in list(group.items()) + [(a, ga), (b, gb)]:
            if v in (ga, gb):
                group[k] = min(ga, gb)
    pats = draft.get("patterns")
    if not isinstance(pats, list) or not pats:
        raise ValueError('patterns = [{"id": "P1", "kind": "...", "what": "...", "examples": [{"n": 2, "quote": "..."}]}]')
    P, out, ids = [], [], set()
    for i, p in enumerate(pats, 1):
        if not isinstance(p, dict):
            P.append(f"pattern {i}: a JSON object")
            continue
        pid = str(p.get("id") or "").strip()
        if not re.fullmatch(r"P\d{1,3}", pid):
            P.append(f"pattern {i}: its id is P1, P2, ... (got {pid!r})")
            continue
        if pid in ids:
            P.append(f"{pid}: two patterns with this id")
            continue
        ids.add(pid)
        kind = str(p.get("kind") or "").strip()
        if kind not in PATTERN_KINDS:
            P.append(f"{pid}: kind is one of {', '.join(PATTERN_KINDS)} (got {kind!r})")
        what = " ".join(str(p.get("what") or "").split())
        if not what:
            P.append(f"{pid}: say in words what repeats (what)")
        elif _COUNTED.search(what):
            P.append(f'{pid}: no count in "what" ("{_COUNTED.search(what).group(0)}") - MotionLab counts the examples')
        mexp = str(p.get("measure") or "").strip()
        exs = []
        for e in p.get("examples") or []:
            if isinstance(e, (int, str)) and str(e).lstrip("#").isdigit():
                e = {"n": int(str(e).lstrip("#"))}
            if not isinstance(e, dict):
                P.append(f'{pid}: an example = {{"n": 3, "quote": "the words of #3 that show it"}}')
                continue
            try:
                en = int(str(e.get("n")).lstrip("#"))
            except (TypeError, ValueError):
                P.append(f"{pid}: an example without its number (n)")
                continue
            if en not in live:
                P.append(f"{pid}: the set has no #{en}")
                continue
            q = str(e.get("quote") or "").strip()
            if not q and not mexp:
                P.append(f"{pid}: #{en} needs its quote - the words of #{en} that show it")
                continue
            if q:
                fq = PR.find_quote(recs[live[en]["id"]]["text"], q)
                if not fq["ok"]:
                    c = fq.get("closest")
                    P.append(f'{pid}: #{en} "{PR._snip(q)}" - {fq["why"].replace("the text", f"#{en}" + chr(39) + "s text")}'
                             + (f'; closest: "{PR._snip(c["text"], 90)}" (line {c["line"]})' if c else ""))
                    continue
                exs.append({"n": en, "quote": fq["text"], "at": fq["at"]})
            else:
                exs.append({"n": en, "quote": "", "at": []})
        members = sorted({e["n"] for e in exs})
        if mexp:
            path, _, val = mexp.partition("=")
            path, val = path.strip(), val.strip().lower()
            if not path or not val:
                P.append(f'{pid}: measure = "<fact>=<value>", e.g. "script.hook.pattern=question"')
            else:
                fits = sorted(n for n, it in live.items() if str(_fact(it, path)).lower() == val)
                for en in members:
                    if en not in fits:
                        P.append(f"{pid}: #{en} does not measure {mexp} (its {path} is {_fact(live[en], path)!r})")
                members = fits
        exc = []
        for x in p.get("except") or []:
            try:
                x = int(str(x).lstrip("#"))
            except (TypeError, ValueError):
                P.append(f"{pid}: except = text numbers")
                continue
            if x not in live:
                P.append(f"{pid}: except #{x} - the set has no #{x}")
            elif x in members:
                P.append(f"{pid}: #{x} is an example and an exception")
            exc.append(x)
        distinct = {group.get(n, n) for n in members}
        if len(distinct) < 2:
            P.append(f"{pid}: 2 different texts at least show a pattern (twins count once) - it has "
                     f"{len(distinct)}")
        rated = sum(1 for n in members if ((recs[live[n]["id"]].get("result") or {}).get("rating")) == "good")
        out.append({"id": pid, "kind": kind, "what": what, "examples": exs, "except": exc,
                    "how_many": f"{len(distinct)} of {len(live)}", "k": len(distinct), "of": len(live),
                    "rated_good": rated, **({"measure": mexp, "items": members} if mexp else {})})
    if P:
        raise ValueError(f"patterns not saved - {_pl(len(P), 'problem')}:\n  " + "\n  ".join(P))
    doc = {"set": S["name"], "date": _now(), "items_sha": _items_sha(list(live.values())),
           "summary": " ".join(str(draft.get("summary") or "").split())[:1500], "patterns": out}
    write_json(set_dir(name) / "patterns.json", doc, indent=1)
    return {"patterns": len(out), "line": f"saved {_pl(len(out), 'pattern')} for {S.get('label') or S['name']}: "
                                          + "; ".join(f"{p['id']} {p['how_many']}" for p in out)}


# ------------------------------------------------------------------------------------------ selfcheck
def selfcheck(verbose: bool = True) -> dict:
    """Known answers in temp folders (a temp set root AND a temp prompt library - never the lab's): splitting (---,
    PROMPT n, a .txt, a .docx with --- lines; kinds guessed, a picked kind kept; duplicates re-used; near twins),
    measuring (the script check stored for scripts / hooks, shared phrases with their numbers), the quotes (verbatim,
    another case / curly quotes / dashes kept as the text's own words with at; pieces out of order, a paraphrase, a
    summary and words from another text refused), the rows (missing with words, clear without, an unknown part, a
    part with no row, a flagged script part clear - refused, accepted with an override; a model the text does not
    name left out), identity (a wrong sha1 refused; a kind change re-found by sha1, its check no longer counting),
    patterns (a number not in the set, a quote not in that text, one example, a typed count - refused; how_many
    counted), verdicts saved and cleared, remove-item, verify_source. Returns {"passed", "checks", "failed",
    "seconds"}."""
    import tempfile
    import zipfile
    global ROOT
    t0 = time.time()
    bad, n_ok = [], 0

    def ok(cond, what):
        nonlocal n_ok
        n_ok += 1
        if not cond:
            bad.append(what)
        if verbose:
            print(("PASS  " if cond else "FAIL  ") + what)

    def refused(fn, *words):
        try:
            fn()
        except ValueError as e:
            msg = str(e)
            return all(w.lower() in msg.lower() for w in words), msg
        return False, "(saved - not refused)"

    tmp = Path(tempfile.mkdtemp(prefix="ml_textsets_"))
    old = (ROOT, PR.HOME, PR.FILES, PR.EXAMPLES, globals()["_styles"])
    try:
        ROOT = tmp / "texts"
        PR.HOME = tmp / "prompts"
        PR.FILES = PR.HOME / "files"
        PR.EXAMPLES = PR.HOME / "examples"
        globals()["_styles"] = lambda: []                 # no analysed references in a test
        img = ("Transform the environment into a cinematic detective investigation room. Keep the person’s face, "
               "identity, and appearance completely unchanged — preserve all facial features exactly as in the "
               "original photo. Convert the surroundings: cluttered desk surfaces, evidence folders, cork boards with "
               "red string, a dim desk lamp casting dramatic shadows. The aesthetic is a gritty psychological "
               "thriller: gritty textures, subtle smoke or dust in the air, a cold desaturated cinematic color "
               "palette.")
        shot = ("@image1 is the start frame. Slow dolly-in on a woman walking through a neon alley at night, rain on "
                "the ground, 35mm lens, shallow depth of field, a cold desaturated cinematic color palette. 5 seconds, "
                "9:16. No text on screen.")
        scr = ("Hey guys, welcome back to my channel. Today I want to talk about editing. Editing is something I do "
               "every day and I really like it a lot. So let's get into it and see what happens with all of this.")
        hook = "Nobody tells you this about editing: one cut doubled my views in a week."
        paste = "\n---\n".join([img, shot, scr, hook])
        sp = split(paste)
        ok([x["i"] for x in sp["items"]] == [1, 2, 3, 4] and sp["new"] == 4 and not sp["unread"],
           f"split: 4 texts between --- lines, numbered #1-#4 (got {[x['i'] for x in sp['items']]})")
        kinds = [x["kind"] for x in sp["items"]]
        ok(kinds == ["image", "shot", "script", "hook"], f"split: kinds guessed image, shot, script, hook (got {kinds})")
        ok(all(x["kind_why"] for x in sp["items"]) and "words" in sp["items"][3]["kind_why"],
           f"split: each guess says why ({sp['items'][3]['kind_why']})")
        sp2 = split(paste, kinds={sp["items"][0]["sha"]: "shot"})
        ok(sp2["items"][0]["kind"] == "shot" and sp2["items"][0]["kind_from"] == "you", "split: a kind the user picked "
                                                                                          "is kept")
        old_fmt = "PROMPT 1\nkind: hook\nsource: tested by me\ntext:\n" + hook + "\n\nPROMPT 2\nkind: shot\ntext:\n" + shot
        sp3 = split(old_fmt)
        ok([x["kind"] for x in sp3["items"]] == ["hook", "shot"], "split: the older PROMPT n blocks, kinds kept")
        PR.FILES.mkdir(parents=True)
        (PR.FILES / "two.txt").write_text(img + "\n---\n" + shot, encoding="utf-8")
        doc = ("<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body>"
               + "".join(f"<w:p><w:r><w:t>{x}</w:t></w:r></w:p>" for x in (hook, "---", scr)) + "</w:body></w:document>")
        with zipfile.ZipFile(PR.FILES / "guide.docx", "w") as z:
            z.writestr("word/document.xml", doc)
        (PR.FILES / "scan.pdf").write_bytes(b"%PDF-1.4\n%nothing readable\n")
        sp4 = split("", ["knowledge/local/prompts/files/two.txt", "guide.docx", "scan.pdf"])
        ok(len(sp4["items"]) == 4 and sp4["items"][0]["from"] == {"file": "two.txt", "part": 1}
           and sp4["items"][2]["from"] == {"file": "guide.docx", "part": 1}
           and [u["file"] for u in sp4["unread"]] == ["scan.pdf"],
           "split: a .txt and a .docx with --- lines = 2 texts each; an unreadable PDF goes to Claude")
        ok(sp4["items"][1]["dup"] is None and split(paste + "\n---\n" + shot)["items"][4]["dup"] == "#2",
           "split: the same words twice = 'same as #2', added once")
        short = split("too short")["items"][0]
        ok(short["problem"].startswith("too short"), "split: under 5 words = too short to check")
        many = split("\n---\n".join(f"text number {k} with a few more words in it" for k in range(MAX_ITEMS + 1)))
        ok(many["too_many"] and many["new"] == MAX_ITEMS + 1, f"split: {MAX_ITEMS + 1} texts = too many")
        before = PR.count()
        r = create("Demo set", "", paste, source={"type": "creator", "creator": "Somebody", "link": "https://x.y/z"})
        S = get_set(r["set"])
        ok(r["set"] == "Demo_set" and r["added"] == 4 and PR.count() == before + 4 and [it["n"] for it in S["items"]]
           == [1, 2, 3, 4], f"create: 4 prompts saved in the library, the set numbered #1-#4 (got {r})")
        ids = {it["n"]: it["id"] for it in S["items"]}
        recs = {n: PR.get(i) for n, i in ids.items()}
        ok(all(rc["text"] in paste for rc in recs.values()) and recs[1]["source"] == {"type": "creator", "creator":
           "Somebody", "link": "https://x.y/z"}, "create: the texts word for word, the source the user picked")
        r2 = create("Demo set", "", hook + "\n---\nA brand new text that nobody has written before in this set.")
        ok(r2["set"] == "Demo_set_2" and r2["reused"] == 1 and r2["added"] == 1,
           f"create: a name in use gets _2; a text the library has is re-used (got {r2})")
        f3 = S["items"][2]["facts"]
        ok(f3.get("script", {}).get("checks") and S["items"][3]["facts"].get("script") and "script" not in
           S["items"][0]["facts"], "measure: the script check stored for the script and the hook only")
        ph = S["summary"]["phrases"]
        ok(any("cold desaturated cinematic color palette" in p["text"] and p["items"] == [1, 2] for p in ph),
           f"measure: the shared phrase found with its numbers ({[(p['text'], p['items']) for p in ph][:3]})")
        ok(S["state"]["checked"] == 0 and S["state"]["left"] == [1, 2, 3, 4] and not S["state"]["done"],
           "state: 0 of 4 checked, all left")
        base = {"set": "Demo_set", "n": 1, "sha1": S["items"][0]["sha1"], "title": "Detective room still",
                "review": {"stars": 4, "why": "Clear locks; says \"cork boards with red string\".", "fix": "Add avoid."}}
        rows1 = [{"slot": "references", "text": "", "status": "missing", "tip": "say what the photo is"},
                 {"slot": "keep", "text": "KEEP THE PERSON'S FACE, identity, and appearance completely unchanged - "
                                          "preserve all facial features", "status": "clear"},
                 {"slot": "change", "text": "Transform the environment into a cinematic detective investigation room",
                  "status": "clear"},
                 {"slot": "setting", "text": "cluttered desk surfaces ... cork boards with red string", "status": "clear"},
                 {"slot": "light", "text": "a dim desk lamp casting dramatic shadows", "status": "clear"},
                 {"slot": "look", "text": "a cold desaturated cinematic color palette", "status": "clear"},
                 {"slot": "materials", "text": "gritty textures, subtle smoke or dust", "status": "clear"},
                 {"slot": "avoid", "text": "", "status": "missing", "tip": "no readable text"}]
        skip1 = {"subject": "the person in the photo is the subject - nothing to describe", "composition": "kept as in "
                 "the photo by the keep part"}
        res = save_check("Demo set", 1, {**base, "structure": rows1, "skipped": skip1})
        rec1 = PR.get(ids[1])
        keep = next(x for x in rec1["structure"] if x["slot"] == "keep")
        s0, e0 = keep["at"][0]
        ok(res["quotes"] == 6 and keep["text"].startswith("Keep the person’s face") and rec1["text"][s0:e0] == keep["text"],
           f"quotes: another case / straight apostrophe / a dash for — accepted, saved as the text's own words + at "
           f"({keep['text'][:40]}…)")
        sett = next(x for x in rec1["structure"] if x["slot"] == "setting")
        ok(len(sett["at"]) == 2 and " … " in sett["text"], f"quotes: pieces left out with ... = 2 spans ({sett['text']})")
        ok(rec1["skipped"] == skip1 and get_set("Demo set")["state"]["checked"] == 1, "save_check: skipped saved, 1 of "
                                                                                      "4 checked")
        line_ok = "1 of 4" in res["line"] and "6 quotes" in res["line"]
        ok(line_ok, f"save_check says it: {res['line']}")
        # the user's verdict per part of Claude's check (the review dialog writes it through /api/prompts/wishes)
        vr = PR.update(ids[1], verdicts={"keep": "wrong", "change": ""})
        ok(vr["verdicts"] == {"keep": "wrong"} and "the user: WRONG" in PR.describe(vr, full=True)
           and get_set("Demo set")["state"]["disputed"] == [1], "verdicts: saved (a cleared part dropped), shown to "
                                                               "Claude, the text counts as disputed")
        ok(refused(lambda: PR.update(ids[1], verdicts={"keep": "maybe"}), "verdicts")[0], "verdicts: another word refused")
        PR.update(ids[1], verdicts={})
        bad_rows = [dict(x) for x in rows1]
        bad_rows[6] = {"slot": "materials", "text": "subtle smoke or dust ... gritty textures", "status": "clear"}
        good, msg = refused(lambda: save_check("Demo set", 1, {**base, "structure": bad_rows, "skipped": skip1}),
                            "earlier", "materials")
        ok(good, f"quotes: pieces out of order refused ({msg.splitlines()[1][:90] if len(msg.splitlines()) > 1 else msg})")
        para = [dict(x) for x in rows1]
        para[0] = {"slot": "references", "text": "the person in the uploaded image", "status": "vague"}
        good, msg = refused(lambda: save_check("Demo set", 1, {**base, "structure": para, "skipped": skip1}),
                            "references", "not in #1's text")
        ok(good, "quotes: a paraphrase refused, with the closest passage")
        summ = [dict(x) for x in rows1]
        summ[4] = {"slot": "light", "text": "one lamp: dim / dramatic / shadows", "status": "clear"}
        ok(refused(lambda: save_check("Demo set", 1, {**base, "structure": summ, "skipped": skip1}), "light")[0],
           "quotes: a summary of the text refused")
        mix = [dict(x) for x in rows1]
        mix[2] = {"slot": "change", "text": "Slow dolly-in on a woman walking through a neon alley", "status": "clear"}
        good, msg = refused(lambda: save_check("Demo set", 1, {**base, "structure": mix, "skipped": skip1}),
                            "those words are #2's")
        ok(good, "quotes: words of another text of the set refused, named as #2's")
        for label, change, words in [
                ("missing with words", lambda R: R.__setitem__(7, {"slot": "avoid", "text": "photo", "status": "missing"}),
                 ("avoid", "quotes nothing")),
                ("clear without words", lambda R: R.__setitem__(0, {"slot": "references", "text": "", "status": "clear"}),
                 ("references", "needs the words")),
                ("an unknown part", lambda R: R.append({"slot": "mood board", "text": "evidence folders", "status": "clear"}),
                 ("mood board", "not a part")),
                ("a part with no row", lambda R: R.pop(5), ("look", "no row"))]:
            R = [dict(x) for x in rows1]
            change(R)
            ok(refused(lambda: save_check("Demo set", 1, {**base, "structure": R, "skipped": skip1}), *words)[0],
               f"rows: {label} refused")
        ok(refused(lambda: save_check("Demo set", 1, {**base, "sha1": "0" * 16, "structure": rows1, "skipped": skip1}),
                   "sha1")[0], "identity: a draft whose sha1 is not #1's refused")
        whyq = {**base, "review": {"stars": 3, "why": "It says \"a warm golden glow\".", "fix": "x"}}
        ok(refused(lambda: save_check("Demo set", 1, {**whyq, "structure": rows1, "skipped": skip1}), "review.why")[0],
           "review: words in double quotes that are not in the text refused")
        w: list = []
        clean, pr = PR.verify_check(recs[2], {"model": "Veo 3 Fast", "structure": None}, warnings=w)
        ok(not pr and "model" not in clean and w, f"model: one the text does not name left out ({w[:1]})")
        sc_rows = [{"slot": "hook", "text": "Hey guys, welcome back to my channel", "status": "clear"},
                   {"slot": "promise", "text": "", "status": "missing"}, {"slot": "problem", "text": "", "status": "missing"},
                   {"slot": "points", "text": "Editing is something I do every day", "status": "vague"},
                   {"slot": "re-hooks", "text": "", "status": "missing"}, {"slot": "proof", "text": "", "status": "missing"},
                   {"slot": "payoff", "text": "", "status": "missing"},
                   {"slot": "call to action", "text": "", "status": "missing"},
                   {"slot": "on screen", "text": "", "status": "missing"}]
        b3 = {"set": "Demo_set", "n": 3, "sha1": S["items"][2]["sha1"]}
        good, msg = refused(lambda: save_check("Demo set", 3, {**b3, "structure": sc_rows}), "hook", "flags it")
        ok(good, "script: a part the measured check flags (a greeting first) marked clear refused")
        res3 = save_check("Demo set", 3, {**b3, "structure": sc_rows, "overrides": {"hook": "the greeting is the joke "
                                                                                             "the video is about"}})
        hk = next(x for x in PR.get(ids[3])["structure"] if x["slot"] == "hook")
        ok(res3["checked"] == 2 and hk.get("override", "").startswith("the greeting"), "script: accepted with an "
                                                                                        "override, kept on the row")
        # identity: a kind change re-finds the text by its words; its check no longer counts
        S0 = get_set("Demo set")
        nk = PR.set_kind(ids[1], "shot")
        S1 = get_set("Demo set")
        it1 = S1["items"][0]
        ok(it1["id"] == nk["id"] and it1["kind"] == "shot" and it1["stale"] and S1["state"]["checked"] == 1
           and S0["state"]["checked"] == 2, f"identity: a kind change ({ids[1]} -> {nk['id']}) re-found by sha1, its "
                                            f"check no longer counts (2 -> {S1['state']['checked']} checked)")
        mv = set_item_kind("Demo set", 1, "image", "a still: no movement, a start frame")
        ok(mv["kind"] == "image" and get_set("Demo set")["items"][0]["stale"] is False
           and get_set("Demo set")["state"]["checked"] == 2, "kind back to image: the stamp counts again")
        # patterns
        pd = {"summary": "Cold palettes.", "patterns": [
            {"id": "P1", "kind": "look", "what": "a cold desaturated cinematic palette",
             "examples": [{"n": 1, "quote": "a cold desaturated cinematic color palette"},
                          {"n": 2, "quote": "A COLD desaturated cinematic color palette"}]}]}
        rp = save_patterns("Demo set", pd)
        P1 = load_patterns("Demo set")["patterns"][0]
        ok(rp["patterns"] == 1 and P1["how_many"] == "2 of 4" and P1["examples"][1]["at"]
           and get_set("Demo set")["state"]["patterns"] == "ok", f"patterns: saved, how_many counted by the tool "
                                                                 f"({P1['how_many']})")
        for label, p, words in [
                ("a number not in the set", {"id": "P1", "kind": "look", "what": "x y", "examples": [{"n": 9, "quote": "a"},
                                                                                                {"n": 1, "quote": "cork boards"}]}, ("no #9",)),
                ("a quote not in that text", {"id": "P1", "kind": "look", "what": "red", "examples": [{"n": 1, "quote": "cork boards"},
                                                                                                 {"n": 2, "quote": "cork boards"}]}, ("#2",)),
                ("one example", {"id": "P1", "kind": "look", "what": "red string", "examples": [{"n": 1, "quote": "cork boards"}]},
                 ("2 different texts",)),
                ("a typed count", {"id": "P1", "kind": "look", "what": "cold palette in 2 of 4",
                                   "examples": [{"n": 1, "quote": "cinematic color palette"}, {"n": 2, "quote": "cinematic color palette"}]},
                 ("no count",))]:
            ok(refused(lambda: save_patterns("Demo set", {"patterns": [p]}), *words)[0], f"patterns: {label} refused")
        sv = save_verdicts("Demo set", {"P1": {"v": "partly", "note": "only the night ones"}})
        sv2 = save_verdicts("Demo set", {"P1": {"v": ""}})
        ok(sv["patterns"]["P1"]["v"] == "partly" and "P1" not in sv2["patterns"], "verdicts: saved, then cleared")
        save_verdicts("Demo set", {"P1": {"v": "correct"}})
        ml = memory_lines()
        ok(any("Demo set" in x and "2 of 4" in x and "correct" in x for x in ml), f"memory_lines: {ml[:1]}")
        rm = remove_item("Demo set", 2)
        S2 = get_set("Demo set")
        ok(rm["count"] == 3 and [it["n"] for it in S2["items"]] == [1, 3, 4] and PR.get(ids[2])
           and S2["state"]["patterns"] == "stale", "remove-item 2: nothing renumbered, the prompt stays in the "
                                                   "library, the patterns are stale")
        # verify_source: Claude's copy of a prompt out of a file must be in the file
        x_ok = {"kind": "hook", "text": hook, "source": {"type": "creator", "file": "guide.docx"}}
        x_bad = {"kind": "hook", "text": "Nobody tells you this about editing: one cut tripled my views.",
                 "source": {"type": "creator", "file": "guide.docx"}}
        notes: list = []
        ok(not PR.verify_source(x_ok) and PR.verify_source(x_bad) and not PR.verify_source(
            {"kind": "hook", "text": hook, "source": {"type": "creator", "file": "scan.pdf"}}, notes) and notes,
           "verify_source: a text in its file passes, a changed one refused, an unreadable file noted")
        ad = add_records("Demo set", [PR.add(x_ok)["id"] if not known(hook) else known(hook)["id"]], ["guide.docx"])
        ok("0 texts added" in ad["line"] or "1 text added" in ad["line"], f"add_records: {ad['line']}")
        L = list_sets()
        ok(len(L) == 2 and L[0]["count"] in (2, 3) and all(s["prompt"].startswith("/analyze-reference texts ") for s in L),
           "list_sets: both sets with their counts and the Claude command")
        ok(any(x.startswith("Text set Demo_set") for x in show("Demo set")) and any("sha1" in x for x in show("Demo set", 3)),
           "show: the set, and one text with its sha1")
    except Exception as e:                                   # noqa: BLE001 - a crash is a failed check, said so
        import traceback
        ok(False, f"crashed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
    finally:
        ROOT, PR.HOME, PR.FILES, PR.EXAMPLES, globals()["_styles"] = old
        shutil.rmtree(tmp, ignore_errors=True)
    secs = round(time.time() - t0, 2)
    if verbose:
        print(f"{n_ok - len(bad)}/{n_ok} checks pass ({secs} s)")
    return {"passed": not bad, "checks": n_ok, "failed": bad, "seconds": secs}
