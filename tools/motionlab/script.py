"""Prepare a video (0.4.x): the words you say on camera. Two ways in - *Improve my script* (the user's script, checked
and rewritten for more reach by `/write-script improve`) and *Write one from zero* (the user's answers to a few
questions -> `/write-script request`).

- `check(text)` = the script check: what a talking script will do on camera, measured from its words - no Claude, no
  tokens, instant (the app runs it while you type). The hook (first sentence, the words of the first 3 s, its
  pattern, a greeting first), the length at a speaking rate (~150 words/min, or the rate MEASURED on the analysed
  videos you pick), short spoken sentences, filler words, the longest stretch with nothing new (no turn, question,
  number or new point), "you" vs "I", numbers, the call to action and where it sits, the last line, the on-screen
  notes. Rules of thumb from creator practice (`.claude\\skills\\write-script\\guidelines.md` explains each); the
  user's own results outrank them.
- Requests = what the app's two dialogs saved: knowledge\\local\\prompts\\requests\\req-NNN.json (private, next to
  the prompt library where the scripts themselves live: kind `script` / `hook`). A script written from a request
  carries `"request": "req-NNN"` (prompts.add). Since 0.4.3 a third kind: `"kind": "title"` = *Title & thumbnail
  first* (`save_title`, for `/write-title request`); the record made from it is a prompt of kind `title`.

A script has no video yet, so its times are estimates in seconds; once it is filmed, timestamps follow the lab's
frame + timecode rule.
"""
from __future__ import annotations

import datetime as _dt
import re
import threading
import time

from . import prompts as PR
from .util import ANALYSIS, read_json, safe_name, write_json

REQUESTS = PR.HOME / "requests"
WPM = 150                       # speaking rate when no analysed video says otherwise: ~2.5 spoken words a second
SHORT_MAX_S = 90                # up to here a short (TikTok / Reels / Shorts): a turn every few seconds
FLAT_S = {"short": (8, 12), "long": (45, 75)}            # longest stretch with nothing new: ok up to / warn up to (s)
WHERE = {"vertical": "TikTok, Reels, Shorts (vertical)", "youtube": "YouTube (horizontal)"}
TONES = {"calm": "calm and clear", "energy": "high energy", "funny": "funny", "story": "storytelling",
         "expert": "expert, no fluff", "raw": "raw and honest"}
CTAS = {"follow": "follow for more", "comment": "comment a word", "save": "save / share it", "link": "link in bio",
        "subscribe": "subscribe", "none": "no ask"}
LANGS = {"es": "Español", "en": "English"}
# 0.4.3 *Title & thumbnail first* (`/write-title request`): where it goes and which way up
PLATFORMS = {"youtube": "YouTube (horizontal video)", "shorts": "YouTube Shorts", "tiktok": "TikTok",
             "instagram": "Instagram Reels"}
ORIENTATIONS = {"horizontal": "horizontal 16:9", "vertical": "vertical 9:16", "both": "horizontal and vertical"}
_LOCK = threading.RLock()

# ------------------------------------------------------------------------------------------------ the words
_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.U)
_ES_W = set("""de la que el en y los se del las un por con no una su para es al lo como más mas pero sus le ya este sí
porque esta entre cuando muy sin sobre también me hasta hay donde desde todo nos durante todos uno les ni otros ese eso
esto mí antes qué unos yo otro otra él tanto esa estos mucho nada muchos poco ella estar estas algo mi mis tú te ti tu
tus os vosotros pues vale aquí así hoy""".split())
_EN_W = set("""the and to of a in is you that it for on with this i my your be are was but so if what how not do at have
just can me we they he she don't it's i'm you're here there when about all one more get""".split())
# number words ("one" / "uno" left out: "no one", "one of", "uno de" are no numbers)
_NUMWORDS = set("""two three four five six seven eight nine ten twelve fifteen twenty thirty fifty hundred thousand
million half double dos tres cuatro cinco seis siete ocho nueve diez doce quince veinte treinta cincuenta cien mil
millón millones mitad doble""".split())
_NUM = r"\b(\d+|" + "|".join(sorted(_NUMWORDS, key=len, reverse=True)) + r")\b"
_YOU = {"en": set("you your you're yours yourself you'll you've you'd".split()),
        "es": set("tú tu tus te ti contigo usted ustedes os vosotros vosotras vuestro vuestra vuestros".split())}
_I = {"en": set("i me my mine myself i'm i've i'll i'd".split()),
      "es": set("yo me mi mis conmigo mío mía".split())}
# a greeting or an announcement before the hook - the first 3 s decide if they stay
_OPENER = re.compile(r"^\W*(hey (guys|everyone|everybody|y'?all|there)|hi (guys|everyone|there)|hello( (guys|everyone|everybody))?|"
                     r"what'?s up|welcome( back)?|in (this|today'?s) video|today,? (i|we)('m| am|'re| are)? "
                     r"(going|gonna)|so,? today|my name is|before we (start|begin)|don'?t forget to|"
                     r"hola|buen(os|as) (días|tardes|noches)|qué tal|que tal|bienvenid[oa]s?|en (este|el) (vídeo|video) de hoy|"
                     r"en este (vídeo|video)|hoy (os|te|les) (voy|vamos)|hoy vamos a|me llamo|antes de empezar|bueno,? pues)\b",
                     re.I)
# hook patterns (prompts.HOOK_PATTERNS), the first that matches the first line
_PATTERNS = [
    ("call-out", r"^\W*(if you('re| are)?|anyone who|for (those|everyone) who|si (eres|tienes|quieres|estás|te)|para (los|las|quienes) que)\b"),
    ("question", r"\?"),
    ("contrarian", r"\b(stop|never|don'?t|nobody|no one|wrong|myth|lie|lies|mistake|overrated|unpopular|deja de|dejad de|nunca|"
                   r"nadie|error|errores|mentira|mito|no hagas|está mal|sobrevalorad[oa])\b"),
    ("number", _NUM),
    ("story", r"\b(i was|when i|last (week|month|year|night)|yesterday|years ago|i (quit|lost|moved|tried|spent|made)|"
              r"cuando (yo )?(era|tenía|empecé|llegué)|el año pasado|ayer|hace \w+ (años|meses|días)|dejé|perdí|me mudé|probé|gasté)\b"),
    ("curiosity gap", r"\b(secret|nobody tells|no one tells|what happened|here'?s (why|what|how)|this is why|the reason|"
                      r"el secreto|nadie te (dice|cuenta)|lo que pasó|por esto|la razón|así es como)\b"),
    ("bold claim", r"\b(best|worst|only|biggest|fastest|easiest|changed my life|the truth|el mejor|la mejor|el peor|la peor|"
                   r"el único|la única|cambió mi vida|la verdad)\b"),
    ("demo", r"^\W*(look at|watch|this is|here'?s|mira|mirad|esto es|aquí tienes)\b"),
]
_FILLERS = {"en": ["basically", "actually", "literally", "honestly", "you know", "i mean", "kind of", "sort of", "so yeah",
                   "like i said", "um", "uh", "anyways"],
            "es": ["básicamente", "literalmente", "o sea", "osea", "en plan", "la verdad es que", "sinceramente", "digamos",
                   "pues nada", "bueno pues", "eh"]}
# something new: a turn anywhere in a sentence, or a list step / a reveal that opens one (a question or a number counts too)
_TURN = re.compile(r"\b(but|however|here'?s the (thing|catch|trick)|the problem|the truth|turns out|except|that'?s when|"
                   r"plot twist|the secret|instead|pero|sin embargo|el problema|la verdad|resulta que|excepto|"
                   r"ahí es cuando|el secreto|en cambio)\b"
                   r"|^\W*(first|second|third|next|finally|step|number|wait|now|so here'?s|and that'?s|primero|segundo|"
                   r"tercero|después|por último|paso|número|espera|ahora|y entonces|y ahí)\b", re.I)
_CTA = re.compile(r"\b(follow|subscribe|comment|save (this|it)|share (this|it)|send (this|it)|link in (my |the )?bio|"
                  r"click the link|sign up|join|dm me|let me know|tag (a|someone|your)|turn on notifications|part (2|two)|"
                  r"sígueme|seguidme|sigue la cuenta|suscríbete|suscribete|comenta|comentad|déjame en (los )?comentarios|"
                  r"guárdalo|guardalo|guarda este|comparte|compártelo|envíaselo|mándaselo|link en (la|mi) bio|enlace en (la|mi) bio|"
                  r"apúntate|escríbeme|etiqueta a|parte 2|segunda parte)\b", re.I)
_WEAK_END = re.compile(r"\b(that'?s (it|all)|bye|see you|peace out|thanks for watching|hope you enjoyed|hope this helps|"
                       r"eso es todo|nada más|chao|adiós|hasta (la próxima|luego|el próximo)|gracias por ver|"
                       r"espero que (os|te) haya gustado|y ya está|pues eso)\b", re.I)
# notes for the camera / the edit, not words to say: [TEXT: ...], (B-ROLL: ...), lines that start with one
_CUE_TAGS = (r"on screen|text|texto|b-?roll|visual|zoom|cut|corte|sfx|music|música|musica|cam|camera|cámara|plano|"
             r"en pantalla|shot|graphic|gráfico|overlay|caption|transition|transición|pause|pausa")
_CUE_BRACKET = re.compile(r"\[[^\]]*\]|\((?:" + _CUE_TAGS + r")\b[^)]*\)", re.I)
_CUE_LINE = re.compile(r"^\s*(?:" + _CUE_TAGS + r")\s*:", re.I)
# section labels ("HOOK (0-3 s)", "## Payoff", "**Part 2**" alone on a line = a heading; "CTA: follow me" = the words
# after the label stay)
_LABELS = (r"(?:hook|gancho|intro|promise|promesa|problem|problema|context|contexto|body|cuerpo|point|punto|part|parte|"
           r"step|paso|proof|prueba|story|historia|payoff|re-?hook|cta|call to action|llamada a la acción|outro|ending|"
           r"final|cierre)(?:\s*\d+)?(?:\s*\([^)]{0,20}\))?")
_HEADING = re.compile(r"^\s*(?:#.*|-{3,}|\*\*[^*]{0,60}\*\*:?|" + _LABELS + r"\s*:?)\s*$", re.I)
_LABEL = re.compile(r"^\s*(?:\*\*)?" + _LABELS + r"(?:\*\*)?\s*[:\-–—]\s*", re.I)
_TIMING = re.compile(r"[\(\[]?(?:\b\d{1,2}(?::\d\d)?\s*(?:s|seg|sec)?\s*[-–]\s*\d{1,2}(?::\d\d)?\s*(?:s|seg|sec)\b"
                     r"|\b\d{1,2}:\d\d\s*[-–]\s*\d{1,2}:\d\d\b)[\)\]]?", re.I)


def _words(s: str) -> list[str]:
    return _WORD.findall(s or "")


def _lang(words: list[str]) -> str:
    low = [w.lower() for w in words[:600]]
    es, en = sum(w in _ES_W for w in low), sum(w in _EN_W for w in low)
    return "" if es + en < 3 else ("es" if es > en else "en")


def spoken(text: str) -> tuple[str, int]:
    """The words to say (labels, timings, headings and notes for the camera taken out) + how many notes there were."""
    cues, out = 0, []
    for ln in str(text or "").replace("\r", "").split("\n"):
        cues += len(_CUE_BRACKET.findall(ln))
        ln = _CUE_BRACKET.sub(" ", ln)
        if _CUE_LINE.match(ln):
            cues += 1
            continue
        s = ln.strip()
        if _HEADING.match(s):
            continue
        s = _LABEL.sub("", s)
        s = _TIMING.sub(" ", s).strip(" -–—*")
        if s:
            out.append(s)
    return "\n".join(out), cues


_CUE_ONE = re.compile(r"\[\s*([^\]:]+?)\s*(?::\s*([^\]]*))?\]|\(\s*(" + _CUE_TAGS + r")\b\s*:?\s*([^)]*)\)", re.I)
_CAPS_HEAD = re.compile(r"^[^a-záéíóúñü]{2,40}$")       # "SOLVE (20-30 s)", "OFFER": a short line in capitals


def cue_cards(text: str) -> list[dict]:
    """Film it (2026-10-15): the script as cue cards, read like spoken() - per part its heading, the lines to say
    (a [check] stays in the line: a fact to confirm before filming) and the notes for the camera / the edit
    ({"tag": "B-ROLL", "text": ...})."""
    parts: list[dict] = []

    def part(head: str) -> dict:
        parts.append({"head": head, "lines": [], "notes": []})
        return parts[-1]

    cur = None
    for ln in str(text or "").replace("\r", "").split("\n"):
        notes = []

        def note(m):
            tag, body = (m[1], m[2]) if m[1] is not None else (m[3], m[4])
            if tag.strip().lower() == "check" and not body:
                return m[0]
            notes.append({"tag": tag.strip().upper(), "text": (body or "").strip()})
            return " "
        rest = _CUE_ONE.sub(note, ln)
        if _CUE_LINE.match(rest):
            tag, _, body = rest.partition(":")
            notes.append({"tag": tag.strip().upper(), "text": body.strip()})
            rest = ""
        s = rest.strip()
        head = s.split(" · ")[0].strip() if " · " in s else s
        if s and (_HEADING.match(head) or (_CAPS_HEAD.match(head) and len(_words(head)) <= 6 and not s.endswith((".", "!", "?")))):
            cur = part(" · ".join(x.strip() for x in s.strip("#* ").rstrip(":").split("·") if x.strip()))
            cur["notes"] += notes
            continue
        lab = _LABEL.match(s)
        if lab:
            cur = part(lab.group(0).strip(" :-–—*"))
            s = s[lab.end():]
        s = _TIMING.sub(" ", s).strip(" -–—*")
        if cur is None and (s or notes):
            cur = part("")
        if cur is not None:
            cur["notes"] += notes
            if s.lower() == "[check]":                    # a note's own [check]: the part has a fact to confirm
                cur["check"] = True
            elif s:
                cur["lines"].append(" ".join(s.split()))
    return [p for p in parts if p["lines"] or p["notes"]]


def sentences(text: str) -> list[str]:
    """Sentences: split at . ! ? … and at line ends (scripts often have one line per sentence, no full stop) - a line
    that goes on in lower case is the same sentence wrapped."""
    text = re.sub(r"(?<![.!?…:;\n])\n(?=[a-záéíóúñü])", " ", text)
    parts = re.split(r"(?<=[.!?…])[\"”»']?\s+|\n+", text)
    return [p.strip() for p in parts if _words(p)]


# ------------------------------------------------------------------------------------------------ the check
_TALK_CACHE: dict = {}


def talk_rate(like: list[str]) -> dict | None:
    """The talking of the analysed videos the user picked (style.merge): words a minute and words in the first 3 s.
    Cached for a minute (the app checks while you type)."""
    key = tuple(like or [])
    if not key:
        return None
    hit = _TALK_CACHE.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    from . import style as ST                            # numpy and the cards: only when references are picked
    # sung lyrics are no speaking rate: music videos are left out (the 4AM video: 177 "words/min" of lyrics)
    talk = [n for n in key if (ST.find(n) or {}).get("category") != "music_video"]
    try:
        t = (ST.build(like=talk) or {}).get("talk") or {} if talk else {}
    except (ValueError, OSError):
        t = {}
    wpm = t.get("words_per_min")
    out = {"wpm": wpm, "hook_words": t.get("hook_words"), "videos": len(talk)} if wpm and wpm >= 60 else None
    _TALK_CACHE[key] = (time.time(), out)
    return out


def _snip(s: str, n: int = 8) -> str:
    w = s.split()
    return " ".join(w[:n]) + ("…" if len(w) > n else "")


def check(text: str, length_s: float | None = None, like: list[str] | None = None, wpm: float | None = None) -> dict:
    """The script check. length_s = the length the user wants (none: no length check, just the estimate); like =
    analysed videos whose MEASURED speaking rate replaces the rule of thumb; wpm = a rate given directly."""
    say, cues = spoken(text)
    words = _words(say)
    n = len(words)
    rate_from = "rule of thumb"
    if not wpm:
        tr = talk_rate(like or [])
        if tr:
            wpm, rate_from = tr["wpm"], f"measured on {tr['videos']} of your analysed video{'s' if tr['videos'] > 1 else ''}"
        elif like:
            rate_from = "rule of thumb - the videos you picked have too little talking to measure"
    wpm = float(wpm or WPM)
    wps = wpm / 60.0
    secs = round(n / wps, 1) if n else 0.0
    lang = _lang(words)
    out: dict = {"lang": lang, "words": n, "seconds": secs, "wpm": round(wpm), "rate_from": rate_from,
                 "format": "short" if (length_s or secs) <= SHORT_MAX_S else "long", "cues": cues, "checks": []}
    if not n:
        out.update(passed=0, total=0)
        return out
    sents = sentences(say)
    lens = [len(_words(s)) for s in sents]
    low = [w.lower() for w in words]
    L = [lang] if lang else ["en", "es"]

    def add(cid, label, status, detail):
        out["checks"].append({"id": cid, "label": label, "status": status, "detail": detail})

    # 1-2. the hook: the first line, the words of the first 3 s, its pattern, no greeting first
    first = sents[0]
    n3 = max(1, round(3 * wps))
    toks = [t for t in say.split() if _WORD.search(t)]     # spoken words with their punctuation
    first3 = " ".join(toks[:n3])
    opener = _OPENER.search(first)
    pattern = next((p for p, rx in _PATTERNS if re.search(rx, first, re.I)), "")
    out["hook"] = {"text": first, "words": lens[0], "first_3s": first3, "pattern": pattern,
                   "opener": opener.group(0).strip(" ,.") if opener else ""}
    if opener:
        add("hook", "Hook in the first 3 s", "bad", f"It opens with “{out['hook']['opener']}” - the first 3 s decide if "
            "people stay: open with your most interesting line, greet later or never.")
    elif lens[0] > 22:
        add("hook", "Hook in the first 3 s", "bad", f"The first sentence is {lens[0]} words (≈ {lens[0] / wps:.0f} s): "
            f"in 3 s they hear only “{_snip(first3, 12)}”. Say the hook in 7-12 words.")
    elif lens[0] > 15:
        add("hook", "Hook in the first 3 s", "warn", f"{lens[0]} words in the first sentence - a bit long for 3 s "
            f"(≈ {n3} words fit). They hear “{_snip(first3, 12)}”.")
    else:
        add("hook", "Hook in the first 3 s", "ok", f"“{_snip(first, 12)}” - {lens[0]} words, ≈ {lens[0] / wps:.1f} s.")
    add("pattern", "A known hook pattern", "ok" if pattern else "warn",
        f"A {pattern} hook." if pattern else "No question, number, bold claim, story, call-out or contrarian line in "
        "the first sentence - give them a reason to wait for the next one.")

    # 3. length
    if length_s:
        diff = (secs - length_s) / length_s
        st = "ok" if abs(diff) <= 0.15 else "warn" if abs(diff) <= 0.3 else "bad"
        add("length", "Length", st, f"≈ {secs:g} s at {round(wpm)} words/min ({rate_from}) for {length_s:g} s wanted"
            + ("" if st == "ok" else f" - {'cut' if diff > 0 else 'add'} ≈ {abs(round(n - length_s * wps))} words."))
    else:
        add("length", "Length", "ok", f"≈ {secs:g} s at {round(wpm)} words/min ({rate_from}) - "
            f"{'a short (TikTok, Reels, Shorts)' if secs <= SHORT_MAX_S else 'long form'}.")

    # 4. short spoken sentences
    avg = sum(lens) / len(lens)
    longest = max(range(len(lens)), key=lambda i: lens[i])
    out["sentences"] = {"count": len(sents), "avg_words": round(avg, 1), "longest": lens[longest],
                        "longest_text": _snip(sents[longest])}
    st = "ok" if avg <= 16 and lens[longest] <= 30 else "bad" if avg > 20 or lens[longest] > 40 else "warn"
    add("sentences", "Short, spoken sentences", st, f"{avg:.0f} words a sentence on average; the longest "
        f"({lens[longest]} words) starts “{_snip(sents[longest], 6)}”" + ("." if st == "ok" else " - split it: one idea a sentence."))

    # 5. fillers
    joined = " " + " ".join(low) + " "
    fl = []
    for lg in L:
        for f in _FILLERS[lg]:
            k = len(re.findall(r"(?<!\w)" + re.escape(f.strip("¿?")) + r"(?!\w)", joined))
            if k:
                fl.append({"w": f, "n": k})
    out["fillers"] = fl
    nf = sum(x["n"] for x in fl) * 150 / max(n, 150)      # per 150 words (a minute of talking)
    add("fillers", "No filler words", "ok" if nf <= 1 else "warn" if nf <= 3 else "bad",
        "None." if not fl else ", ".join(f"“{x['w']}” ×{x['n']}" for x in fl) + " - cut them: every word has to earn its second.")

    # 6. something new every few seconds (short) / every minute (long): turns, questions, numbers, list steps
    marks, pos = [], 0
    for s, k in zip(sents, lens):
        if pos and (_TURN.search(s) or "?" in s or re.search(_NUM, s, re.I)):
            marks.append(pos)
        pos += k
    edges = [lens[0]] + [m for m in marks if m > lens[0]] + [n]
    gaps = [(edges[i + 1] - edges[i], edges[i]) for i in range(len(edges) - 1)]
    g, at = max(gaps) if gaps else (0, 0)
    ok_s, warn_s = FLAT_S[out["format"]]
    flat_s = round(g / wps, 1)
    start = " ".join(toks[at:at + 6])
    out["flat"] = {"seconds": flat_s, "start": start, "turns": len(marks)}
    st = "ok" if flat_s <= ok_s else "warn" if flat_s <= warn_s else "bad"
    add("rehooks", "Something new every few seconds" if out["format"] == "short" else "A re-hook every minute", st,
        f"{len(marks)} turns, questions or numbers after the hook; the longest stretch without one is ≈ {flat_s:g} s"
        + (f", from “{start}…”" if st != "ok" and start else "")
        + ("." if st == "ok" else f" - add a turn (but / here's the thing), a question or a number every ≈ {ok_s} s."))

    # 7. talks to the viewer
    you = sum(w in _YOU[lg] for w in low for lg in L)
    me = sum(w in _I[lg] for w in low for lg in L)
    out["you"], out["i"] = you, me
    add("you", "Talks to the viewer", "ok" if you >= max(1, me // 3) else "warn",
        f"“you” ×{you}, “I” ×{me}" + ("." if you >= max(1, me // 3) else
                                       " - make it about them: what THEY get, feel or should do."))

    # 8. concrete details
    nums = sum(1 for w in low if w.isdigit() or w in _NUMWORDS)
    out["numbers"] = nums
    want = max(1, round(secs / 30))
    add("specifics", "Concrete details", "ok" if nums >= want else "warn",
        f"{nums} number{'s' if nums != 1 else ''}" + ("." if nums >= want else
                                                     " - a number, a name, a price or a time frame makes it believable (one every ≈ 30 s)."))

    # 9. one call to action, near the end
    ctas = [(m.start() / max(1, len(say)), m.group(0)) for m in _CTA.finditer(say)]
    out["cta"] = [{"text": t, "at": round(a, 2)} for a, t in ctas]
    kinds = {t.lower().split()[0] for _, t in ctas}
    late = [t for a, t in ctas if a >= 0.75]
    if not ctas:
        add("cta", "One call to action at the end", "warn", "No ask - end with ONE specific action and a reason "
            "(“comment GUIDE and I'll send it”, “follow for part 2”).")
    elif len(kinds) > 2:
        add("cta", "One call to action at the end", "warn", f"{len(kinds)} different asks ({', '.join(sorted(kinds))}) - "
            "one ask works better than three.")
    elif not late:
        add("cta", "One call to action at the end", "warn", f"“{ctas[0][1]}” comes early - an ask before the value costs "
            "viewers; move it to the last seconds.")
    else:
        line = next((s for s in reversed(sents) if _CTA.search(s)), late[-1])
        add("cta", "One call to action at the end", "ok", f"“{_snip(line, 10)}” in the last seconds.")

    # 10. the last line
    last = sents[-1]
    weak = _WEAK_END.search(last)
    out["ending"] = {"text": last, "weak": weak.group(0) if weak else ""}
    add("ending", "A strong last line", "warn" if weak else "ok",
        f"Ends on “{weak.group(0)}” - end on the payoff or the ask (or a line that loops back to the first one)."
        if weak else f"“{_snip(last, 10)}”")

    # 11. what is on screen
    add("cues", "What is on screen", "ok" if cues else "warn",
        f"{cues} note{'s' if cues != 1 else ''} for the camera / the edit." if cues else
        "No notes like [TEXT: ...] or [B-ROLL: ...] - say what is on screen while you talk, or the edit has to guess.")
    out["passed"] = sum(1 for c in out["checks"] if c["status"] == "ok")
    out["total"] = len(out["checks"])
    return out


def text_report(c: dict) -> str:
    """The check as text (tools\\script.py, Claude)."""
    mark = {"ok": "✓", "warn": "~", "bad": "✗"}
    lines = [f"{c['words']} words ≈ {c['seconds']:g} s at {c['wpm']} words/min ({c['rate_from']}); language "
             f"{c['lang'] or '?'}; {c.get('passed', 0)} of {c.get('total', 0)} checks pass"]
    lines += [f"  {mark[x['status']]} {x['label']}: {x['detail']}" for x in c["checks"]]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ requests
def _clean(v, n: int = 1000) -> str:
    return " ".join(str(v or "").split())[:n]


def _lines(v, n: int = 3000) -> str:
    return "\n".join(" ".join(ln.split()) for ln in str(v or "").splitlines() if ln.strip())[:n]


def _like(v) -> list[str]:
    from . import style as ST
    like = [_clean(x, 160) for x in (v or []) if str(x).strip()]
    if len(like) > ST.MAX_REFS:
        raise ValueError(f"at most {ST.MAX_REFS} videos for one style")
    for x in like:
        if ST.find(x) is None:
            raise ValueError(f"no analysed video called {x!r}")
    return like


def _length(v) -> float | None:
    if v in (None, ""):
        return None
    v = float(v)
    if not 5 <= v <= 3600:
        raise ValueError("length: 5 seconds to 60 minutes")
    return v


def _next_req() -> str:
    nums = [int(p.stem[4:]) for p in REQUESTS.glob("req-*.json") if p.stem[4:].isdigit()]
    return f"req-{max(nums, default=0) + 1:03d}"


def _save(req: dict) -> dict:
    with _LOCK:
        req = {"id": _next_req(), **req, "date": _dt.datetime.now().isoformat(timespec="seconds")}
        write_json(REQUESTS / f"{req['id']}.json", req, indent=1)
    return req


def save_new(body: dict) -> dict:
    """*Write one from zero*: the user's answers, checked -> a request for `/write-script request <id>`."""
    topic = _lines(body.get("topic"), 1500)
    if not topic:
        raise ValueError("say what the video is about first")
    where = body.get("where") or ""
    if where and where not in WHERE:
        raise ValueError(f"where: one of {', '.join(WHERE)}")
    tone = body.get("tone") or ""
    if tone and tone not in TONES:
        raise ValueError(f"tone: one of {', '.join(TONES)}")
    cta = body.get("cta") or ""
    if cta and cta not in CTAS:
        raise ValueError(f"call to action: one of {', '.join(CTAS)}")
    lang = _clean(body.get("lang"), 30)
    req = {"kind": "new", "topic": topic, "audience": _lines(body.get("audience")), "takeaway": _lines(body.get("takeaway")),
           "angle": _lines(body.get("angle"), 3000), "points": _lines(body.get("points")), "length_s": _length(body.get("length_s")),
           "where": where, "tone": tone, "cta": cta, "cta_text": _clean(body.get("cta_text"), 300), "lang": lang,
           "like": _like(body.get("like")), "extra": _lines(body.get("extra"))}
    return _save(req)


def save_improve(body: dict) -> dict:
    """*Improve my script*: the user's script -> the prompt library (kind script, the user's own) + a request with what
    they want (length, where, style, their words) for `/write-script improve <script id>`."""
    text = str(body.get("text") or "").replace("\r", "").strip()
    if len(_words(spoken(text)[0])) < 5:
        raise ValueError("paste your script first (at least a sentence)")
    if len(text) > 100_000:
        raise ValueError("a script up to 100,000 characters")
    where = body.get("where") or ""
    if where and where not in WHERE:
        raise ValueError(f"where: one of {', '.join(WHERE)}")
    like, length = _like(body.get("like")), _length(body.get("length_s"))
    file = _clean(body.get("file"), 200)
    refs = [x for x in like if safe_name(x) == x and (ANALYSIS / x).is_dir()]   # a friend's card has no analysis here
    rec = PR.add({"kind": "script", "text": text, "source": {"type": "tested", **({"file": file} if file else {})},
                  "style_refs": refs})
    req = _save({"kind": "improve", "script": rec["id"], "want": _lines(body.get("want")), "length_s": length,
                 "where": where, "like": like})
    return {"script": rec, "request": req}


def save_title(body: dict) -> dict:
    """*Title & thumbnail first* (0.4.3, Prepare): the user's answers, checked -> a request with `"kind": "title"`
    for `/write-title request <id>` (about 10 titles, 2-3 thumbnail concepts with the shot to film, the hook).
    The script requests stay as they were (kind new / improve).

    body (the app's dialog; only the topic is required):
      topic        str, what the video is about (required)
      viewer       str, who it is for
      angle        str, the user's story / result / opinion - what makes it theirs
      platforms    list of PLATFORMS keys: youtube / shorts / tiktok / instagram (several allowed; empty = Claude
                   asks or defaults to youtube)
      orientation  horizontal / vertical / both (empty = from the platforms: youtube -> horizontal, the rest ->
                   vertical, both kinds -> both)
      language     str, e.g. "es", "en" or a name
      style_refs   list of analysed videos (analysis folder names or friends' cards, style.find), up to style.MAX_REFS
      notes        str, anything else
    Returns the saved request {id: req-NNN, kind: title, ..., date}; raises ValueError with a plain message."""
    topic = _lines(body.get("topic"), 1500)
    if not topic:
        raise ValueError("say what the video is about first")
    plats = body.get("platforms") or []
    if isinstance(plats, str):
        plats = [x.strip() for x in plats.replace(",", " ").split() if x.strip()]
    plats = list(dict.fromkeys(str(x).lower() for x in plats))
    bad = [x for x in plats if x not in PLATFORMS]
    if bad:
        raise ValueError(f"platforms: {', '.join(PLATFORMS)} (got {', '.join(bad)})")
    orient = str(body.get("orientation") or "").lower()
    if orient and orient not in ORIENTATIONS:
        raise ValueError(f"orientation: one of {', '.join(ORIENTATIONS)}")
    if not orient and plats:
        h, v = "youtube" in plats, any(x != "youtube" for x in plats)
        orient = "both" if h and v else "horizontal" if h else "vertical"
    req = {"kind": "title", "topic": topic, "viewer": _lines(body.get("viewer")), "angle": _lines(body.get("angle"), 3000),
           "platforms": plats, "orientation": orient, "language": _clean(body.get("language"), 30),
           "style_refs": _like(body.get("style_refs")), "notes": _lines(body.get("notes"))}
    return _save(req)


def requests() -> list[dict]:
    """Every saved request, newest first, with what was made from it (new / title: records whose `request` is its
    id - scripts and hooks, or title & thumbnail records; improve: the script it improves and the versions made from
    that one)."""
    out = []
    items = PR.load_all("script") + PR.load_all("hook") + PR.load_all("title")
    for p in sorted(REQUESTS.glob("req-*.json"), reverse=True):
        try:
            r = read_json(p)
        except (OSError, ValueError):
            continue
        if r.get("kind") in ("new", "title"):
            r["made"] = [x["id"] for x in items if x.get("request") == r.get("id")]
        else:
            r["made"] = [x["id"] for x in items if r.get("script") in (x.get("made_from") or [])]
        out.append(r)
    return out


def get_request(rid: str) -> dict:
    if not re.fullmatch(r"req-\d{3,}", str(rid)):
        raise ValueError(f"not a request id: {rid!r} (like req-001)")
    p = REQUESTS / f"{rid}.json"
    if not p.exists():
        raise ValueError(f"no request {rid}")
    return read_json(p)


def request_of(script_id: str) -> dict | None:
    """The newest *Improve my script* request of a script (what the user wants from the rewrite)."""
    for p in sorted(REQUESTS.glob("req-*.json"), reverse=True):
        try:
            r = read_json(p)
        except (OSError, ValueError):
            continue
        if r.get("kind") == "improve" and r.get("script") == script_id:
            return r
    return None


def request_path(rid: str):
    get_request(rid)
    return REQUESTS / f"{rid}.json"


def describe_request(r: dict) -> str:
    """A request as text for Claude."""
    rows = [("about", r.get("topic")), ("for", r.get("audience")), ("they get", r.get("takeaway")),
            ("the user's angle", r.get("angle")), ("must say", r.get("points")),
            ("length", f"{r['length_s']:g} s" if r.get("length_s") else ""), ("where", WHERE.get(r.get("where") or "", "")),
            ("tone", TONES.get(r.get("tone") or "", "")),
            ("call to action", " - ".join(x for x in (CTAS.get(r.get("cta") or "", ""), r.get("cta_text")) if x)),
            ("language", LANGS.get(r.get("lang") or "", r.get("lang") or "")), ("style like", ", ".join(r.get("like") or [])),
            ("what the user wants", r.get("want")), ("also", r.get("extra"))]
    if r.get("kind") == "title":                         # 0.4.3 *Title & thumbnail first*
        rows = [("about", r.get("topic")), ("for", r.get("viewer")), ("the user's angle", r.get("angle")),
                ("platforms", ", ".join(PLATFORMS.get(x, x) for x in r.get("platforms") or [])),
                ("orientation", ORIENTATIONS.get(r.get("orientation") or "", "")),
                ("language", LANGS.get(r.get("language") or "", r.get("language") or "")),
                ("style like", ", ".join(r.get("style_refs") or [])), ("also", r.get("notes"))]
    head = (f"{r.get('id')} - write a script from zero" if r.get("kind") == "new"
            else f"{r.get('id')} - title & thumbnail first (before filming)" if r.get("kind") == "title"
            else f"{r.get('id')} - improve {r.get('script')}") + f" ({str(r.get('date', ''))[:16]})"
    return "\n".join([head] + [f"  {k}: {v}" for k, v in rows if v])
