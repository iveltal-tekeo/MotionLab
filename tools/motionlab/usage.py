"""What it took (0.4.4): Claude's minutes and tokens, read from Claude Code's own session logs - read-only.

Claude Code writes every session of this lab to %USERPROFILE%\\.claude\\projects\\<lab>\\<session>.jsonl (<lab> = the
lab's path with every character that is not a letter or a digit as '-': C:\\MotionLab -> C--MotionLab), one JSON line
per event, and a session's helpers (subagents) to <session>\\subagents\\agent-<id>.jsonl + .meta.json. This module only
READS those files: it never writes there and never talks to Claude Code (no hook, no status line, no message), so a
session's context and tokens are exactly the same with MotionLab open or closed. What it read stays in memory: a log
is read again only when its size or time changed (~1 s for 400 MB of logs, the big request copies skipped unparsed);
`live()` reads only the bytes added since its last look.

A session -> rounds. A round = one prompt (yours, the app's first message, or a background task's notice) and every
answer until the next prompt; local commands (/effort, /model, /clear) are not rounds. Per round: when, minutes
(Claude Code's own `turn_duration` when it wrote one, else the first to the last event of the round), tokens counted
once per answer (one answer = several lines with the same message.id and the same usage), models, effort, skill
(`attributionSkill`) and what it was for:
  - a lab skill's command (/recreate-video improve X, /write-script request req-002 ...) -> that task + its words;
  - answers tagged with a lab skill -> that task + the words of the session's last command (or of its name);
  - a background task's notice right after a counted round (a render finished) -> the same as that round;
  - anything else (questions, other work in the same window, after /clear) = not counted for any video.
The app names the sessions it opens ("MotionLab recreate <video>", system.claude_launcher); the name's words count when
a round's own words name nothing. `objects()` turns words into the lab's projects / analyses / requests / prompts.
The log format is Claude Code's, not a public API: a line it does not know is skipped, a number it cannot read is
"not measured" - never a guess.

    .venv\\Scripts\\python tools\\usage.py sessions | project <p> | analysis <name> | check | selfcheck
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from motionlab import i18n as I18N
from motionlab.util import LAB, safe_name

# lab skill -> the task it does (system.TASKS names the app's sessions with the same words)
LAB_SKILLS = {"analyze-reference": "review", "recreate-video": "recreate", "generate-video": "generate",
              "write-script": "script", "write-title": "title", "write-prompt": "prompt"}
# the app's session names: "MotionLab <task word> <label>" (system.TASKS)
TITLE_TASKS = {"review": "review", "feedback": "feedback", "recreate": "recreate", "generate": "generate",
               "script": "script", "title": "title", "prompt": "prompt", "lessons": "lessons", "library": "library",
               "next": "plan"}
# lines never needed: copies of the requests (the biggest), file backups, attachments, UI state
SKIP = (b'{"type":"api-request', b'{"type":"file-history', b'{"type":"attachment', b'{"type":"queue-operation',
        b'{"type":"mode"', b'{"type":"permission-mode"', b'{"type":"atis-latch"', b'{"type":"last-prompt"',
        b'{"type":"ai-title"', b'{"type":"agent-name"')
TOKEN_KEYS = (("input", "input_tokens"), ("cache_write", "cache_creation_input_tokens"),
              ("cache_read", "cache_read_input_tokens"), ("output", "output_tokens"))
LIVE_WINDOW_S = 120          # a log that grew in the last 2 min = a session at work
MESSAGE = "<message>"        # live(): the user's message came in (not a tool) - _step() says "reading your message"
STEP_INPUT = ("description", "file_path", "path", "skill")   # what _step() reads of a tool's input (live() keeps these)
_lock = threading.Lock()
_cache: dict[str, tuple[int, int, dict]] = {}       # log path -> (size, mtime_ns, session)
_live: dict[str, dict] = {}                         # log path -> what live() read so far


def log_dir(lab: Path = LAB) -> Path:
    """Where Claude Code keeps this lab's sessions (CLAUDE_CONFIG_DIR moves ~\\.claude)."""
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return base / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(lab))


def _ts(s) -> float | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
    return ""


def _is_result(content) -> bool:
    return isinstance(content, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content)


def _command(text: str) -> tuple[str, str] | None:
    """'<command-name>/write-script</command-name> ... <command-args>request req-002</command-args>' -> (name, args)."""
    m = re.search(r"<command-name>/?([\w:.-]+)</command-name>", text)
    if not m:
        return None
    a = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
    return m.group(1), (a.group(1).strip() if a else "")


def _prompt_words(text: str) -> str:
    """A prompt in a few plain words for the lists (no tags, no pasted blocks)."""
    c = _command(text)
    if c:
        return f"/{c[0]} {c[1]}".strip()
    t = re.sub(r"<pasted_content[^>]*>(.*?)</pasted_content[^>]*>", r"\1", text, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:160]


def model_name(m: str | None) -> str:
    """'claude-opus-5-5' -> 'Opus 5.5' (an unknown id stays as it is)."""
    g = re.fullmatch(r"claude-([a-z]+)-(\d+)-(\d+)(?:-\d{8})?", str(m or ""))
    return f"{g[1].capitalize()} {g[2]}.{g[3]}" if g else str(m or "?")


def _tokens0() -> dict:
    return {k: 0 for k, _ in TOKEN_KEYS}


def _add_usage(tok: dict, u: dict) -> None:
    for k, src in TOKEN_KEYS:
        v = u.get(src)
        if isinstance(v, (int, float)):
            tok[k] += int(v)


def total(tok: dict) -> int:
    """Everything the model read and wrote: new input + cache written + cache read + output."""
    return sum(tok.get(k, 0) for k, _ in TOKEN_KEYS)


def _lines(path: Path, start: int = 0):
    """(offset after the line, raw line) for every complete line from `start`."""
    with open(path, "rb") as fh:
        fh.seek(start)
        pos = start
        for raw in fh:
            if not raw.endswith(b"\n"):
                return                                   # still being written: read next time
            pos += len(raw)
            yield pos, raw


# ------------------------------------------------------------------------------------------------- one session
def _helpers(sdir: Path) -> list[dict]:
    """A session's helpers (subagents): type, description, model, tokens, first / last time."""
    out = []
    for f in sorted((sdir / "subagents").glob("agent-*.jsonl")) if (sdir / "subagents").is_dir() else []:
        meta = {}
        try:
            meta = json.loads(f.with_suffix(".meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        tok, ids, models, t0, t1 = _tokens0(), set(), Counter(), None, None
        for _, raw in _lines(f):
            if raw.startswith(SKIP):
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            t = _ts(d.get("timestamp"))
            if t:
                t0, t1 = min(t0 or t, t), max(t1 or t, t)
            m = d.get("message") if d.get("type") == "assistant" else None
            if isinstance(m, dict) and m.get("id") and m["id"] not in ids and isinstance(m.get("usage"), dict) \
                    and m.get("model") != "<synthetic>":
                ids.add(m["id"])
                _add_usage(tok, m["usage"])
                models[m.get("model")] += 1
        out.append({"id": f.stem, "type": meta.get("agentType"), "description": meta.get("description"),
                    "tool_use": meta.get("toolUseId"), "model": models.most_common(1)[0][0] if models else meta.get("model"),
                    "effort": meta.get("effort"), "tokens": tok, "answers": len(ids), "t0": t0, "t1": t1})
    return out


def read_session(path: Path) -> dict:
    """One log -> the session: its name, rounds (see the module's notes), helpers, the sessions it continues in, and
    Claude Code's own cost notes (`cost-state`, one per run - for the hand check only)."""
    path = Path(path)
    title, cont, costs, events, bad, seq = None, [], {}, [], 0, 0
    for _, raw in _lines(path):
        if raw.startswith(SKIP):
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            bad += 1
            continue
        if not isinstance(d, dict):
            continue
        ty = d.get("type")
        if ty == "custom-title":
            title = d.get("customTitle") or title
            continue
        if ty == "continued-in":
            if d.get("continuedInSessionId"):
                cont.append(d["continuedInSessionId"])
            continue
        if ty == "cost-state":
            costs[d.get("startTime")] = d                # written again at each exit: the last one per run
            continue
        if d.get("isSidechain"):
            continue
        t = _ts(d.get("timestamp"))
        if t is None:
            continue
        seq += 1
        if ty == "user":
            if d.get("isMeta"):
                continue
            c = (d.get("message") or {}).get("content")
            if _is_result(c):
                events.append((t, seq, "result", None))
            else:
                txt = _text(c)
                if txt.lstrip().startswith(("<local-command-stdout>", "<local-command-stderr>", "<local-command-caveat>")):
                    continue
                events.append((t, seq, "prompt", (txt, (d.get("origin") or {}).get("kind"))))
        elif ty == "assistant":
            events.append((t, seq, "answer", d))
        elif ty == "system":
            events.append((t, seq, "td" if d.get("subtype") == "turn_duration" else "sys", d.get("durationMs")))
    events.sort(key=lambda e: (e[0], e[1]))

    rounds, cur, ids = [], None, set()
    for t, _, kind, x in events:
        if kind == "prompt":
            txt, origin = x
            cmd = _command(txt)
            cur = {"t0": t, "t1": t, "td": None, "prompt": _prompt_words(txt), "origin": origin or "human",
                   "command": cmd, "answers": 0, "tokens": _tokens0(), "models": Counter(), "efforts": Counter(),
                   "skills": Counter(), "agents": [], "helpers": [], "end_turn": False, "last": None, "marks": []}
            rounds.append(cur)
            continue
        if cur is None:
            continue
        cur["t1"] = max(cur["t1"], t)
        if kind == "td":
            cur["td"] = (x or 0) / 1000
        elif kind == "answer":
            m = x.get("message") or {}
            content = m.get("content") if isinstance(m.get("content"), list) else []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    cur["last"] = (c.get("name"), c.get("input") or {})
                    if c.get("name") in ("Agent", "Task"):
                        cur["agents"].append(c.get("id"))
                    # what each tool touched (a path, a command): a batch round's time is split by it (split())
                    cur["marks"].append((t, json.dumps(c.get("input") or {}, ensure_ascii=False)[:240]))
            cur["end_turn"] = m.get("stop_reason") == "end_turn"
            mid = m.get("id")
            if not mid or mid in ids or not isinstance(m.get("usage"), dict) or m.get("model") == "<synthetic>":
                continue
            ids.add(mid)
            cur["answers"] += 1
            _add_usage(cur["tokens"], m["usage"])
            cur["models"][m.get("model")] += 1
            if x.get("effort"):
                cur["efforts"][x["effort"]] += 1
            if x.get("attributionSkill"):
                cur["skills"][x["attributionSkill"]] += 1
    # local commands (/effort, /clear ...) are no rounds - but /clear ends what came before
    out = []
    for r in rounds:
        if r["answers"] == 0 and r["command"] and r["command"][0] not in LAB_SKILLS:
            if r["command"][0] == "clear":
                out.append({"clear": True, "t0": r["t0"]})
            continue
        r["minutes"] = round((r["td"] if r["td"] is not None else r["t1"] - r["t0"]) / 60, 2)
        out.append(r)
    helpers = _helpers(path.with_suffix(""))
    real = [r for r in out if not r.get("clear")]
    for h in helpers:                                    # a helper's tokens count in the round that started it
        home = next((r for r in real if h["tool_use"] and h["tool_use"] in r["agents"]), None)
        if home is None and h["t0"]:
            home = next((r for r in reversed(real) if r["t0"] <= h["t0"]), None)
        (home or (real[-1] if real else {"helpers": []}))["helpers"].append(h)
    st = path.stat()
    return {"id": path.stem, "file": path.name, "title": title, "rounds": out, "continued_in": cont,
            "costs": list(costs.values()), "bad_lines": bad, "size": st.st_size, "mtime": st.st_mtime,
            "t0": real[0]["t0"] if real else None, "t1": max((r["t1"] for r in real), default=None)}


def _title_task(title: str | None) -> tuple[str | None, str]:
    """'MotionLab recreate prompt → testing' -> ('recreate', 'prompt → testing'); not the app's name -> (None, '')."""
    m = re.fullmatch(r"MotionLab\s+(\S+)\s*(.*)", str(title or ""), re.S)
    if not m:
        return None, ""
    return TITLE_TASKS.get(m[1].lower()), m[2].strip()


def link(session: dict, before: dict | None = None) -> dict:
    """Each round -> `task` (a LAB_SKILLS value or None = not counted), `mode` (the command's first word: request,
    improve, package...) and `words` (the text that names its video / analysis / script). `before` = the last counted
    round of the session this one continues (a `continued-in` line)."""
    ttask, tlabel = _title_task(session.get("title"))
    last, prev = before, None
    for r in session["rounds"]:
        if r.get("clear"):
            last, prev = None, None
            continue
        r["task"], r["mode"], r["words"] = None, "", ""
        cmd = r["command"] if r["command"] and r["command"][0] in LAB_SKILLS else None
        top = next((s for s, _ in r["skills"].most_common() if s in LAB_SKILLS), None)
        if cmd:
            r["task"] = LAB_SKILLS[cmd[0]]
            r["mode"] = (cmd[1].split() or [""])[0].lower()
            r["words"] = cmd[1] + (" " + tlabel if ttask == r["task"] else "")
        elif top:
            r["task"] = LAB_SKILLS[top]
            src = last if last and last["task"] == r["task"] else None
            r["mode"] = src["mode"] if src else ""
            r["words"] = src["words"] if src else (tlabel if ttask == r["task"] else r["prompt"])
        elif r["origin"] == "task-notification" and prev is not None:
            r["task"], r["mode"], r["words"] = prev["task"], prev["mode"], prev["words"]
        if r["task"] and ttask == "feedback" and r["task"] == "review" and not cmd:
            r["task"] = "feedback"
        if r["task"]:
            last = prev = r
        else:
            prev = None
    session["last_counted"] = last
    return session


def sessions(root: Path | None = None) -> list[dict]:
    """Every session of this lab, oldest first, linked (see link()). Re-reads only the logs that changed."""
    root = Path(root) if root else log_dir()
    if not root.is_dir():
        return []
    with _lock:
        seen, out = set(), []
        for e in os.scandir(root):
            if not e.name.endswith(".jsonl") or not e.is_file():
                continue
            st = e.stat()
            sub = Path(e.path).with_suffix("") / "subagents"
            mt = max([st.st_mtime_ns] + ([x.stat().st_mtime_ns for x in os.scandir(sub)] if sub.is_dir() else []))
            seen.add(e.path)
            hit = _cache.get(e.path)
            if not hit or hit[0] != st.st_size or hit[1] != mt:
                try:
                    hit = (st.st_size, mt, read_session(Path(e.path)))
                except OSError:
                    continue
                _cache[e.path] = hit
            out.append(hit[2])
        for k in [k for k in _cache if k.startswith(str(root)) and k not in seen]:
            del _cache[k]
    out.sort(key=lambda s: s["t0"] or 0)
    by_id = {s["id"]: s for s in out}
    prev_of = {c: s["id"] for s in out for c in s["continued_in"]}
    for s in out:                                        # oldest first: a continuation sees its parent's link
        p = by_id.get(prev_of.get(s["id"], ""))
        link(s, p.get("last_counted") if p else None)
    return out


# ------------------------------------------------------------------------------------------------- objects
def objects(words: str, names: dict) -> set[tuple[str, str]]:
    """The lab objects a round's words name: names = {"project": set, "analysis": set, "request": set, "prompt": set}.
    A label cut short or with a character cmd changed still matches by the name inside it; a video's file name finds
    its analysis folder (util.safe_name)."""
    w = str(words or "")
    found = set()
    sw = safe_name(w) if names.get("analysis") else None     # once, not once per analysis name (it depends on w only)
    for kind in names:                                   # project, analysis, request, prompt, thumbs (0.4.5) ...
        for n in names.get(kind, ()):
            if n and (n in w or (kind == "analysis" and sw == n)):
                found.add((kind, n))
    for tok in re.findall(r"[^\s'\"]+", w):              # a quoted path to the video: its stem -> its analysis
        stem = safe_name(Path(tok.rstrip(",")).stem)
        if stem in names.get("analysis", ()):
            found.add(("analysis", stem))
    if any(k == "project" for k, _ in found):            # a project named inside another's name: keep the longest
        ps = sorted((n for k, n in found if k == "project"), key=len, reverse=True)
        found = {x for x in found if x[0] != "project" or not any(len(o) > len(x[1]) and x[1] in o for o in ps)}
    return found


def split(r: dict, names: dict, kind: str) -> dict[str, float]:
    """A batch round (one prompt, many videos: `/analyze-reference batch ...`) -> minutes per object of `kind`: the
    time from one tool call to the next goes to the object the last tool named (a path like analysis\\<name>, a
    command with the name); time before the first named object is nobody's. Scaled so the parts add up to the round's
    own minutes at most (Claude Code's turn_duration). Measured from the log, not shared out evenly."""
    marks = sorted(r.get("marks") or [])
    if not marks or r["t1"] <= r["t0"]:
        return {}
    ends = [t for t, _ in marks[1:]] + [r["t1"]]
    focus, secs = None, {}
    for (t, text), end in zip(marks, ends):
        found = [n for k, n in objects(text, names) if k == kind]
        if found:
            focus = max(found, key=len)
        if focus:
            secs[focus] = secs.get(focus, 0.0) + max(0.0, end - t)
    scale = min(1.0, r["minutes"] * 60 / (r["t1"] - r["t0"]))
    return {n: round(s * scale / 60, 2) for n, s in secs.items()}


def counted(sess: list[dict], names: dict) -> list[tuple[dict, dict, set]]:
    """(session, round, objects) for every counted round, oldest first."""
    out = []
    for s in sess:
        for r in s["rounds"]:
            if r.get("task"):
                out.append((s, r, objects(r["words"], names)))
    return out


def round_info(s: dict, r: dict) -> dict:
    """A round in plain fields for the app."""
    tok = {k: r["tokens"][k] for k, _ in TOKEN_KEYS}
    helpers = [{"type": h["type"], "description": h["description"], "model": model_name(h["model"]),
                "tokens": total(h["tokens"])} for h in r["helpers"]]
    for h in r["helpers"]:
        for k, _ in TOKEN_KEYS:
            tok[k] += h["tokens"][k]
    model = r["models"].most_common(1)[0][0] if r["models"] else None
    return {"session": s["id"], "window": s["title"], "t0": r["t0"], "t1": r["t1"], "minutes": r["minutes"],
            "measured": r["td"] is not None, "task": r.get("task"), "mode": r.get("mode", ""),
            "prompt": r["prompt"], "model": model_name(model) if model else None,
            "effort": r["efforts"].most_common(1)[0][0] if r["efforts"] else None,
            "tokens": tok, "total": total(tok), "helpers": helpers, "answers": r["answers"]}


# ------------------------------------------------------------------------------------------------- live
def _step(name: str | None, inp: dict) -> str:
    """The last tool Claude used, in words ("reading the contact sheets", "rendering v2" = its own description, as
    Claude wrote it). Only the app's live line shows it: in the app's language (Settings > Language, 2026-10-19)."""
    n = str(name or "")
    if n == MESSAGE:
        return I18N.t("reading your message")
    if n in ("Bash", "PowerShell"):
        d = str(inp.get("description") or "").strip()
        return (d[0].lower() + d[1:])[:70] if d else I18N.t("running a command")
    f = Path(str(inp.get("file_path") or inp.get("path") or "")).name
    if n == "Read":
        if not f:
            return I18N.t("reading")
        return I18N.t("looking at {file}", file=f) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) \
            else I18N.t("reading {file}", file=f)
    if n in ("Write", "Edit", "NotebookEdit"):
        return I18N.t("writing {file}", file=f) if f else I18N.t("writing")
    if n in ("Grep", "Glob"):
        return I18N.t("searching the files")
    if n in ("Agent", "Task"):
        return I18N.t("a helper: {what}", what=str(inp.get("description") or I18N.t("working"))[:60])
    if n == "Skill":
        return I18N.t("using /{skill}", skill=str(inp.get("skill") or I18N.t("a skill")))
    if n.startswith("Web"):
        return I18N.t("searching the web")
    if n.startswith("mcp__motionlab__"):
        sees = n.split("__")[-1] in ("sheet", "frames", "stills", "overlay_stills")
        return I18N.t("looking at contact sheets and frames") if sees else I18N.t("reading the lab's data")
    if n.startswith("mcp__davinci-resolve__"):
        return I18N.t("working in DaVinci Resolve")
    return I18N.t("thinking") if not n else n


def live(root: Path | None = None, now: float | None = None) -> list[dict]:
    """The sessions the app opened ("MotionLab ...") that are working now: their log grew in the last 2 min and the
    last answer is not the end of a turn. Per log, only the bytes added since the last call are read (an offset);
    nothing is read for a log that did not grow. -> [{session, title, task, label, minutes, tokens, model, effort,
    step}] - minutes since the current prompt, tokens of the whole session so far. The step is kept as the last tool
    (its name + the few input fields _step reads) and put in words when asked: the app's language of that moment."""
    root = Path(root) if root else log_dir()
    now = now or time.time()
    if not root.is_dir():
        return []
    out = []
    with _lock:
        for e in os.scandir(root):
            if not e.name.endswith(".jsonl"):
                continue
            try:
                st = e.stat()
            except OSError:
                continue
            if now - st.st_mtime > LIVE_WINDOW_S:
                continue
            s = _live.setdefault(e.path, {"off": 0, "title": None, "ids": set(), "tok": 0, "t0": None, "t_last": None,
                                          "tool": None, "model": None, "effort": None, "ended": False})
            if st.st_size < s["off"]:                    # rewritten: start again
                s.update(off=0, ids=set(), tok=0)
            if st.st_size > s["off"]:
                for pos, raw in _lines(Path(e.path), s["off"]):
                    s["off"] = pos
                    if raw.startswith(SKIP):
                        continue
                    try:
                        d = json.loads(raw)
                    except ValueError:
                        continue
                    ty = d.get("type")
                    if ty == "custom-title":
                        s["title"] = d.get("customTitle") or s["title"]
                        continue
                    if d.get("isSidechain"):
                        continue
                    t = _ts(d.get("timestamp"))
                    if t:
                        s["t_last"] = max(s["t_last"] or t, t)
                    if ty == "user" and not d.get("isMeta"):
                        c = (d.get("message") or {}).get("content")
                        if not _is_result(c) and not _text(c).lstrip().startswith("<local-command"):
                            s["t0"], s["ended"], s["tool"] = t, False, (MESSAGE, {})
                    elif ty == "assistant":
                        m = d.get("message") or {}
                        for c in m.get("content") if isinstance(m.get("content"), list) else []:
                            if isinstance(c, dict) and c.get("type") == "tool_use":
                                inp = c.get("input") or {}
                                s["tool"] = (c.get("name"), {k: inp.get(k) for k in STEP_INPUT})
                        s["ended"] = m.get("stop_reason") == "end_turn"
                        if m.get("id") and m["id"] not in s["ids"] and isinstance(m.get("usage"), dict):
                            s["ids"].add(m["id"])
                            s["tok"] += total({k: m["usage"].get(src, 0) or 0 for k, src in TOKEN_KEYS})
                            s["model"] = m.get("model") or s["model"]
                            s["effort"] = d.get("effort") or s["effort"]
            task, label = _title_task(s["title"])
            if not (s["title"] or "").startswith("MotionLab ") or s["ended"] or not s["t0"]:
                continue
            out.append({"session": Path(e.path).stem, "title": s["title"], "task": task, "label": label,
                        "minutes": round((now - s["t0"]) / 60, 1), "tokens": s["tok"],
                        "model": model_name(s["model"]) if s["model"] else None, "effort": s["effort"],
                        "step": _step(*s["tool"]) if s["tool"] else ""})
    return out


# ------------------------------------------------------------------------------------------------- hand check
def check(sess: list[dict]) -> list[dict]:
    """Our sums against Claude Code's own `cost-state` note (one per run of the program), for sessions whose single
    note covers the whole log (the run started with the session, nothing continued into or out of it, no helpers):
    the OUTPUT tokens must agree within 1 %. Cache reads are shown, not judged: Claude Code's note also counts its own
    side calls (the auto-mode permission check, naming the session) - measured 2026-10-15: 0-7 % more cache reads on
    this PC's sessions - which are not answers in the log, so What it took leaves them out."""
    out = []
    continued = {c for s in sess for c in s["continued_in"]}
    for s in sess:
        if len(s["costs"]) != 1 or any(r.get("helpers") for r in s["rounds"] if not r.get("clear")):
            continue
        st = s["costs"][0].get("startTime")
        if s["continued_in"] or s["id"] in continued or not isinstance(st, (int, float)) or not s["t0"] \
                or st / 1000 > s["t0"] + 60:
            continue
        mine, models = _tokens0(), set()
        for r in s["rounds"]:
            if not r.get("clear"):
                _add_usage(mine, {src: r["tokens"][k] for k, src in TOKEN_KEYS})
                models |= set(r["models"])
        # the models that answered in the log only (Claude Code's Haiku side calls - page summaries, titles - are not)
        mu = {m: v for m, v in (s["costs"][0].get("modelUsage") or {}).items() if m in models}
        if not mine["output"]:
            continue
        theirs = {"cache_read": sum(v.get("cacheReadInputTokens", 0) for v in mu.values()),
                  "output": sum(v.get("outputTokens", 0) for v in mu.values())}
        dev = {k: abs(mine[k] - theirs[k]) / max(theirs[k], 1) for k in theirs}
        out.append({"session": s["id"], "title": s["title"], "mine": mine, "theirs": theirs,
                    "ok": dev["output"] <= 0.01, "dev": {k: round(v * 100, 2) for k, v in dev.items()}})
    return out


# ------------------------------------------------------------------------------------------------- self-check
SAMPLES = LAB / "tools" / "dev" / "usage_samples"


def selfcheck(verbose: bool = True) -> dict:
    """Known answers on the fixed sample logs in tools\\dev\\usage_samples (no real session is read): rounds, minutes
    (turn_duration vs first-to-last), an answer written as 2 lines counted once, an untagged follow-up and the work
    after /clear not counted, a background notice counted with its round, a helper's tokens in the round that started
    it, the objects; then live() on a copy that grows. Returns {"passed", "checks"}."""
    import shutil
    import tempfile
    t_start = time.time()
    bad, n = [], 0

    def ok(cond, what):
        nonlocal n
        n += 1
        if not cond:
            bad.append(what)
        if verbose:
            print(("PASS  " if cond else "FAIL  ") + what)

    names = {"project": {"demo_proj", "demo"}, "analysis": {"Video_by_someone_X1"}, "request": {"req-900"},
             "prompt": {"script-900"}}
    S = sessions(SAMPLES)
    by = {s["id"]: s for s in S}
    a, b = by.get("sample-named"), by.get("sample-hand")
    ok(a is not None and b is not None, "both sample sessions read")
    if a and b:
        ra = [r for r in a["rounds"] if not r.get("clear")]
        ok(len(ra) == 2, f"named session: 2 rounds (got {len(ra)})")
        ok(a["title"] == "MotionLab script req-900", "its name read")
        ok(ra[0]["task"] == "script" and ra[0]["mode"] == "request", "round 1 = the script request")
        ok(ra[0]["minutes"] == 2.0, f"round 1 = 2.0 min from turn_duration (got {ra[0]['minutes']})")
        ok(ra[0]["tokens"] == {"input": 3, "cache_write": 100, "cache_read": 3000, "output": 150},
           f"answer of 2 lines counted once (got {ra[0]['tokens']})")
        ok(ra[1]["task"] is None, "an untagged follow-up is not counted")
        ok(objects(ra[0]["words"], names) == {("request", "req-900")}, "its words name req-900")
        ok(a["bad_lines"] == 1, "a broken line skipped, not fatal")
        rb = [r for r in b["rounds"] if not r.get("clear")]
        ok(len(rb) == 3, f"hand session: 3 rounds, /effort and /clear are not rounds (got {len(rb)})")
        ok(rb[0]["task"] == "recreate" and rb[0]["mode"] == "improve", "round 1 = /recreate-video improve")
        ok(rb[0]["minutes"] == 5.0, f"no turn_duration: first to last event = 5.0 min (got {rb[0]['minutes']})")
        ok(rb[1]["task"] == "recreate" and rb[1]["minutes"] == 0.5, "a background notice continues it (0.5 min)")
        ok(rb[2]["task"] is None, "work after /clear is not counted")
        ok(objects(rb[0]["words"], names) == {("project", "demo_proj")}, "demo_proj named (not demo inside it)")
        h = rb[0]["helpers"]
        ok(len(h) == 1 and h[0]["tokens"]["output"] == 500, "the helper's tokens in the round that started it")
        info = round_info(b, rb[0])
        ok(info["total"] == 4 + 200 + 8000 + 300 + 10500 and info["model"] == "Opus 5.5",
           f"round total incl. the helper = 19004 (got {info['total']})")
        ok(model_name("claude-fable-5-1") == "Fable 5.1" and model_name("claude-haiku-4-5-20251001") == "Haiku 4.5",
           "model names")
        c = check(S)
        ok(len(c) == 1 and c[0]["ok"], f"hand check against Claude Code's cost note (got {c})")
    bt = by.get("sample-batch")
    if bt:
        rr = [r for r in bt["rounds"] if not r.get("clear")]
        ok(len(rr) == 1 and rr[0]["task"] == "review" and rr[0]["mode"] == "batch", "a batch round: the review task, mode batch")
        sp = split(rr[0], {"analysis": {"vid_a", "vid_b"}}, "analysis")
        ok(sp == {"vid_a": 5.0, "vid_b": 5.0}, f"a batch split by what each tool touched: 5 + 5 min (got {sp})")
    else:
        ok(False, "the sample batch session read")
    # live: a copy that grows - only the new bytes are read, a finished turn drops out
    tmp = Path(tempfile.mkdtemp(prefix="ml_usage_"))
    try:
        src = (SAMPLES / "sample-named.jsonl").read_bytes().splitlines(keepends=True)
        cut = next(i for i, ln in enumerate(src) if b'"stop_reason":"end_turn"' in ln)
        f = tmp / "live.jsonl"
        f.write_bytes(b"".join(src[:cut]))
        t_now = _ts("2026-10-15T10:01:00Z")
        os.utime(f, (t_now, t_now))
        L = live(tmp, now=t_now + 5)
        ok(len(L) == 1 and L[0]["tokens"] == 1152 and L[0]["minutes"] == 1.1 and L[0]["step"] == "run the checks",
           f"live: working, tokens so far, minutes, the step (got {L})")
        off = _live[str(f)]["off"]
        with open(f, "ab") as fh:
            fh.write(b"".join(src[cut:]))
        os.utime(f, (t_now, t_now))
        L2 = live(tmp, now=t_now + 10)
        ok(_live[str(f)]["off"] > off and L2 == [], "live: reads on from its offset; the turn ended -> gone")
    finally:
        _live.pop(str(tmp / "live.jsonl"), None)
        shutil.rmtree(tmp, ignore_errors=True)
    if verbose:
        print(f"{n - len(bad)}/{n} checks pass ({time.time() - t_start:.2f} s)")
    return {"passed": not bad, "checks": n, "failed": bad}
