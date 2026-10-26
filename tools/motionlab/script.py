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
  first* (`save_title`, for `/write-title request`); the record made from it is a prompt of kind `title`. Since
  2026-10-19 a fourth: `"kind": "prompt"` = the prompt library's *Generate a new prompt* / *Use it, change…*
  (`save_prompt`, for `/write-prompt request`), so the user's words never pass through cmd.

A script has no video yet, so its times are estimates in seconds; once it is filmed, timestamps follow the lab's
frame + timecode rule.
"""
from __future__ import annotations

import datetime as _dt
import re
import threading
import time
import types

from . import i18n as I18N
from . import prompts as PR
from .util import ANALYSIS, read_json, safe_name, write_json

# i18n's t / tn / num, always in English: for words that are STORED (a text set's facts in set.json, package.json's
# checks - "Claude's stored knowledge stays English", the user 2026-10-18). check(..., I18N=ENGLISH) builds them; the
# default I18N = the app's language (Settings > Language), for the page
ENGLISH = types.SimpleNamespace(t=lambda en, **v: I18N.text({}, en, v),
                                tn=lambda n, one, other, **v: I18N.count({}, "en", n, one, other, v),
                                num=lambda v, lg=None: I18N.num(v, "en"))

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
    found = {n: ST.find(n) or {} for n in key}
    # sung lyrics are no speaking rate: music videos are left out (the 4AM video: 177 "words/min" of lyrics)
    talk = [n for n in key if found[n].get("category") != "music_video"]
    try:
        t = (ST.build(like=talk) or {}).get("talk") or {} if talk else {}
    except (ValueError, OSError):
        t = {}
    wpm = t.get("words_per_min")
    friends: dict = {}                                    # 2026-10-18: whose videos the rate was measured on
    for n in talk:
        if found[n].get("origin") == "shared":
            a = found[n].get("author") or "a friend"
            friends[a] = friends.get(a, 0) + 1
    out = {"wpm": wpm, "hook_words": t.get("hook_words"), "videos": len(talk),
           "mine": len(talk) - sum(friends.values()), "friends": friends} if wpm and wpm >= 60 else None
    _TALK_CACHE[key] = (time.time(), out)
    return out


def _measured_on(tr: dict, I18N=I18N) -> str:
    """"measured on 1 of your videos and 1 of tekeo's" - the videos a speaking rate came from, whose they are."""
    n = tr.get("mine", tr.get("videos", 0))
    parts = [I18N.t("{n} of your analysed videos", n=n)] if n else []   # "1 of your videos", "2 of your videos"
    parts += [I18N.t("{n} of {name}'s", n=k, name=a) for a, k in (tr.get("friends") or {}).items()]
    if not parts:
        return I18N.t("measured on {n} analysed videos", n=tr.get("videos", 0))
    said = parts[0]
    for p in parts[1:]:
        said = I18N.t("{a} and {b}", a=said, b=p)
    return I18N.t("measured on {videos}", videos=said)


def _snip(s: str, n: int = 8) -> str:
    w = s.split()
    return " ".join(w[:n]) + ("…" if len(w) > n else "")


def as_g(x: float):
    """x as f"{x:g}" writes it, as a number i18n.num writes in the language (12.0 -> 12, 4.5 -> 4.5 / 4,5)."""
    v = float(f"{x:g}")
    return int(v) if v.is_integer() else v


def check(text: str, length_s: float | None = None, like: list[str] | None = None, wpm: float | None = None, *,
          I18N=I18N) -> dict:
    """The script check. length_s = the length the user wants (none: no length check, just the estimate); like =
    analysed videos whose MEASURED speaking rate replaces the rule of thumb; wpm = a rate given directly. The words
    (labels, details, rate_from) are in the app's language - Prepare checks while you type; I18N=ENGLISH = in English
    (a text set stores the check in its facts)."""
    say, cues = spoken(text)
    words = _words(say)
    n = len(words)
    num = I18N.num
    rate_from = I18N.t("rule of thumb")
    if not wpm:
        tr = talk_rate(like or [])
        if tr:
            wpm, rate_from = tr["wpm"], _measured_on(tr, I18N)
        elif like:
            rate_from = I18N.t("rule of thumb - the videos you picked have too little talking to measure")
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
    hook = I18N.t("Hook in the first 3 s")
    if opener:
        add("hook", hook, "bad", I18N.t("It opens with “{opener}” - the first 3 s decide if people stay: open with your "
                                        "most interesting line, greet later or never.", opener=out["hook"]["opener"]))
    elif lens[0] > 22:
        add("hook", hook, "bad", I18N.t("The first sentence is {n} words (≈ {s} s): in 3 s they hear only “{heard}”. Say "
                                        "the hook in 7-12 words.", n=lens[0], s=round(lens[0] / wps),
                                        heard=_snip(first3, 12)))
    elif lens[0] > 15:
        add("hook", hook, "warn", I18N.t("{n} words in the first sentence - a bit long for 3 s (≈ {fit} words fit). They "
                                         "hear “{heard}”.", n=lens[0], fit=n3, heard=_snip(first3, 12)))
    else:
        add("hook", hook, "ok", I18N.tn(lens[0], "“{first}” - {n} words, ≈ {s} s.", "“{first}” - {n} words, ≈ {s} s.",
                                        first=_snip(first, 12), s=num(round(lens[0] / wps, 1))))
    add("pattern", I18N.t("A known hook pattern"), "ok" if pattern else "warn",
        I18N.t("A {pattern} hook.", pattern=I18N.t(pattern)) if pattern else
        I18N.t("No question, number, bold claim, story, call-out or contrarian line in the first sentence - give them "
               "a reason to wait for the next one."))

    # 3. length
    rate = {"secs": num(as_g(secs)), "wpm": round(wpm), "rate": rate_from}
    if length_s:
        diff = (secs - length_s) / length_s
        st = "ok" if abs(diff) <= 0.15 else "warn" if abs(diff) <= 0.3 else "bad"
        want, k = num(as_g(length_s)), abs(round(n - length_s * wps))
        add("length", I18N.t("Length"), st,
            I18N.t("≈ {secs} s at {wpm} words/min ({rate}) for {want} s wanted", want=want, **rate) if st == "ok" else
            I18N.t("≈ {secs} s at {wpm} words/min ({rate}) for {want} s wanted - cut ≈ {k} words.", want=want, k=k,
                   **rate) if diff > 0 else
            I18N.t("≈ {secs} s at {wpm} words/min ({rate}) for {want} s wanted - add ≈ {k} words.", want=want, k=k,
                   **rate))
    else:
        add("length", I18N.t("Length"), "ok",
            I18N.t("≈ {secs} s at {wpm} words/min ({rate}) - a short (TikTok, Reels, Shorts).", **rate)
            if secs <= SHORT_MAX_S else I18N.t("≈ {secs} s at {wpm} words/min ({rate}) - long form.", **rate))

    # 4. short spoken sentences
    avg = sum(lens) / len(lens)
    longest = max(range(len(lens)), key=lambda i: lens[i])
    out["sentences"] = {"count": len(sents), "avg_words": round(avg, 1), "longest": lens[longest],
                        "longest_text": _snip(sents[longest])}
    st = "ok" if avg <= 16 and lens[longest] <= 30 else "bad" if avg > 20 or lens[longest] > 40 else "warn"
    sv = {"avg": round(avg), "n": lens[longest], "start": _snip(sents[longest], 6)}
    add("sentences", I18N.t("Short, spoken sentences"), st,
        I18N.t("{avg} words a sentence on average; the longest ({n} words) starts “{start}”.", **sv) if st == "ok" else
        I18N.t("{avg} words a sentence on average; the longest ({n} words) starts “{start}” - split it: one idea a "
               "sentence.", **sv))

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
    add("fillers", I18N.t("No filler words"), "ok" if nf <= 1 else "warn" if nf <= 3 else "bad",
        I18N.t("None.|fillers") if not fl else
        I18N.t("{fillers} - cut them: every word has to earn its second.",
               fillers=", ".join(f"“{x['w']}” ×{x['n']}" for x in fl)))

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
    fv = {"s": num(as_g(flat_s)), "start": start, "every": ok_s}
    add("rehooks", I18N.t("Something new every few seconds") if out["format"] == "short" else
        I18N.t("A re-hook every minute"), st,
        I18N.tn(len(marks), "{n} turns, questions or numbers after the hook; the longest stretch without one is ≈ {s} s.",
                "{n} turns, questions or numbers after the hook; the longest stretch without one is ≈ {s} s.", **fv)
        if st == "ok" else
        I18N.tn(len(marks), "{n} turns, questions or numbers after the hook; the longest stretch without one is ≈ {s} s, "
                            "from “{start}…” - add a turn (but / here's the thing), a question or a number every ≈ "
                            "{every} s.",
                "{n} turns, questions or numbers after the hook; the longest stretch without one is ≈ {s} s, from "
                "“{start}…” - add a turn (but / here's the thing), a question or a number every ≈ {every} s.", **fv)
        if start else
        I18N.tn(len(marks), "{n} turns, questions or numbers after the hook; the longest stretch without one is ≈ {s} s "
                            "- add a turn (but / here's the thing), a question or a number every ≈ {every} s.",
                "{n} turns, questions or numbers after the hook; the longest stretch without one is ≈ {s} s - add a "
                "turn (but / here's the thing), a question or a number every ≈ {every} s.", **fv))

    # 7. talks to the viewer
    you = sum(w in _YOU[lg] for w in low for lg in L)
    me = sum(w in _I[lg] for w in low for lg in L)
    out["you"], out["i"] = you, me
    add("you", I18N.t("Talks to the viewer"), "ok" if you >= max(1, me // 3) else "warn",
        I18N.t("“you” ×{you}, “I” ×{me}.", you=you, me=me) if you >= max(1, me // 3) else
        I18N.t("“you” ×{you}, “I” ×{me} - make it about them: what THEY get, feel or should do.", you=you, me=me))

    # 8. concrete details
    nums = sum(1 for w in low if w.isdigit() or w in _NUMWORDS)
    out["numbers"] = nums
    want = max(1, round(secs / 30))
    add("specifics", I18N.t("Concrete details"), "ok" if nums >= want else "warn",
        I18N.tn(nums, "{n} number.", "{n} numbers.") if nums >= want else
        I18N.tn(nums, "{n} number - a number, a name, a price or a time frame makes it believable (one every ≈ 30 s).",
                "{n} numbers - a number, a name, a price or a time frame makes it believable (one every ≈ 30 s)."))

    # 9. one call to action, near the end
    ctas = [(m.start() / max(1, len(say)), m.group(0)) for m in _CTA.finditer(say)]
    out["cta"] = [{"text": t, "at": round(a, 2)} for a, t in ctas]
    kinds = {t.lower().split()[0] for _, t in ctas}
    late = [t for a, t in ctas if a >= 0.75]
    one_cta = I18N.t("One call to action at the end")
    if not ctas:
        add("cta", one_cta, "warn", I18N.t("No ask - end with ONE specific action and a reason (“comment GUIDE and I'll "
                                           "send it”, “follow for part 2”)."))
    elif len(kinds) > 2:
        add("cta", one_cta, "warn", I18N.t("{n} different asks ({asks}) - one ask works better than three.",
                                           n=len(kinds), asks=", ".join(sorted(kinds))))
    elif not late:
        add("cta", one_cta, "warn", I18N.t("“{ask}” comes early - an ask before the value costs viewers; move it to the "
                                           "last seconds.", ask=ctas[0][1]))
    else:
        line = next((s for s in reversed(sents) if _CTA.search(s)), late[-1])
        add("cta", one_cta, "ok", I18N.t("“{line}” in the last seconds.", line=_snip(line, 10)))

    # 10. the last line
    last = sents[-1]
    weak = _WEAK_END.search(last)
    out["ending"] = {"text": last, "weak": weak.group(0) if weak else ""}
    add("ending", I18N.t("A strong last line"), "warn" if weak else "ok",
        I18N.t("Ends on “{end}” - end on the payoff or the ask (or a line that loops back to the first one).",
               end=weak.group(0)) if weak else f"“{_snip(last, 10)}”")

    # 11. what is on screen
    add("cues", I18N.t("What is on screen"), "ok" if cues else "warn",
        I18N.tn(cues, "{n} note for the camera / the edit.", "{n} notes for the camera / the edit.") if cues else
        I18N.t("No notes like [TEXT: ...] or [B-ROLL: ...] - say what is on screen while you talk, or the edit has to "
               "guess."))
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
        raise ValueError(I18N.t("at most {n} videos for one style", n=ST.MAX_REFS))
    for x in like:
        if ST.find(x) is None:
            raise ValueError(I18N.t("no analysed video called {name}", name=repr(x)))
    return like


LIKE_PROMPT_KINDS = ("script", "hook")


def _like_prompts(v) -> list[str]:
    """Prepare's *In the style of > Scripts & hooks* (2026-10-18, the user: "only look in style of "prompts" or
    "videos" they already analize"): up to 3 scripts / hooks of the prompt library, checked against it."""
    from . import style as ST
    ids = list(dict.fromkeys(_clean(x, 40) for x in (v or []) if str(x).strip()))
    if len(ids) > ST.MAX_REFS:
        raise ValueError(I18N.t("at most {n} scripts or hooks for one style", n=ST.MAX_REFS))
    for x in ids:
        if not re.fullmatch(r"(script|hook)-\d{3,}", x):
            raise ValueError(I18N.t("not a script or a hook of your library: {id}", id=repr(x)))
        PR.get(x)                                        # ValueError "no prompt <id>" when it is not in the library
    return ids


def _length(v) -> float | None:
    if v in (None, ""):
        return None
    v = float(v)
    if not 5 <= v <= 3600:
        raise ValueError(I18N.t("length: 5 seconds to 60 minutes"))
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
        raise ValueError(I18N.t("say what the video is about first"))
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
           "like": _like(body.get("like")), "like_prompts": _like_prompts(body.get("like_prompts")),
           "extra": _lines(body.get("extra")), **_brand(body)}
    return _save(req)


def _brand(body: dict) -> dict:
    """0.6.0 For my brand: {"brand": My Brand as it is now} when the user ticked it (and My Brand holds anything)."""
    from . import brand as BR
    snap = BR.snapshot() if body.get("brand") else None
    return {"brand": snap} if snap else {}


def save_improve(body: dict) -> dict:
    """*Improve my script*: the user's script -> the prompt library (kind script, the user's own) + a request with what
    they want (length, where, style, their words) for `/write-script improve <script id>`."""
    text = str(body.get("text") or "").replace("\r", "").strip()
    if len(_words(spoken(text)[0])) < 5:
        raise ValueError(I18N.t("paste your script first (at least a sentence)"))
    if len(text) > 100_000:
        raise ValueError(I18N.t("a script up to 100,000 characters"))
    where = body.get("where") or ""
    if where and where not in WHERE:
        raise ValueError(f"where: one of {', '.join(WHERE)}")
    like, length = _like(body.get("like")), _length(body.get("length_s"))
    like_prompts = _like_prompts(body.get("like_prompts"))      # checked before the script is saved
    file = _clean(body.get("file"), 200)
    refs = [x for x in like if safe_name(x) == x and (ANALYSIS / x).is_dir()]   # a friend's card has no analysis here
    rec = PR.add({"kind": "script", "text": text, "source": {"type": "tested", **({"file": file} if file else {})},
                  "style_refs": refs})
    # replace (2026-10-24, a friend's ask: "only the improved script stays"): once Claude saved the new version, the
    # app moves this pasted copy to the Recycle Bin (motionlab.app.data.tidy_improved) - never one filmed / used
    req = _save({"kind": "improve", "script": rec["id"], "want": _lines(body.get("want")), "length_s": length,
                 "where": where, "like": like, "like_prompts": like_prompts, "replace": True, **_brand(body)})
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
      like_prompts list of scripts / hooks of the prompt library (ids), up to style.MAX_REFS (2026-10-18)
      notes        str, anything else
    Returns the saved request {id: req-NNN, kind: title, ..., date}; raises ValueError with a plain message."""
    topic = _lines(body.get("topic"), 1500)
    if not topic:
        raise ValueError(I18N.t("say what the video is about first"))
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
           "style_refs": _like(body.get("style_refs")), "like_prompts": _like_prompts(body.get("like_prompts")),
           "notes": _lines(body.get("notes")), **_brand(body)}
    return _save(req)


def save_prompt(body: dict) -> dict:
    """The prompt library's *Generate a new prompt from zero* and *Use it, change…* (2026-10-19 - the audit: the wish
    went to Claude on the cmd line, cut at 600 characters, and lost % & | < >): the user's words, checked -> a request
    with `"kind": "prompt"` for `/write-prompt request <id>` (the skill reads it with `tools\\script.py show <id>`).

    body: kind (a prompt kind, prompts.KINDS), want (what to make; required unless `from` is given), from (a prompt
    id: keep its structure and wording), change (what to change in it), for (list: what it is for - vlog, sfx ...),
    model (the model or tool), style_refs (up to style.MAX_REFS analysed videos to copy the style of, style.find).
    Returns the saved request {id: req-NNN, kind: prompt, ..., date}; raises ValueError with a plain message."""
    kind = str(body.get("kind") or "")
    if kind not in PR.KINDS:
        raise ValueError(f"kind: one of {', '.join(PR.KINDS)}")
    src = _clean(body.get("from"), 40)
    if src:
        PR.get(src)                                      # ValueError "no prompt <id>" when it is not in the library
    want, change = _lines(body.get("want"), 6000), _lines(body.get("change"), 6000)
    if not want and not src:
        raise ValueError(I18N.t("say what you want to make first"))
    tags = list(dict.fromkeys(_clean(x, 40).lower() for x in body.get("for") or [] if str(x).strip()))[:12]
    req = {"kind": "prompt", "prompt_kind": kind, "want": want, "from": src, "change": change, "for": tags,
           "model": _clean(body.get("model"), 160), "style_refs": _like(body.get("style_refs"))}
    return _save(req)


def requests() -> list[dict]:
    """Every saved request, newest first, with what was made from it (new / title: records whose `request` is its
    id - scripts and hooks, or title & thumbnail records; improve: the script it improves and the versions made from
    that one)."""
    out, by_kind = [], {}
    items = PR.load_all("script") + PR.load_all("hook") + PR.load_all("title")
    for p in sorted(REQUESTS.glob("req-*.json"), reverse=True):
        try:
            r = read_json(p)
        except (OSError, ValueError):
            continue
        if r.get("kind") in ("new", "title"):
            r["made"] = [x["id"] for x in items if x.get("request") == r.get("id")]
        elif r.get("kind") == "prompt":                  # 2026-10-19: what /write-prompt wrote from it
            k = r.get("prompt_kind") or ""
            if k not in by_kind:
                by_kind[k] = PR.load_all(k)
            r["made"] = [x["id"] for x in by_kind[k] if x.get("request") == r.get("id")]
        else:
            r["made"] = [x["id"] for x in items if r.get("script") in (x.get("made_from") or [])]
        out.append(r)
    return out


def get_request(rid: str) -> dict:
    if not re.fullmatch(r"req-\d{3,}", str(rid)):
        raise ValueError(f"not a request id: {rid!r} (like req-001)")
    p = REQUESTS / f"{rid}.json"
    if not p.exists():
        raise ValueError(I18N.t("no request {id}", id=rid))
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


def _videos_words(keys) -> str:
    """The picked videos for Claude: "<name> (<key>; this PC | from tekeo)" - the key is what style.py takes, a
    friend's card is marked as a friend's (2026-10-18; before, a friend's card reached Claude as a bare video id)."""
    from . import knowledge as KN
    from . import style as ST
    out = []
    for k in keys or []:
        c = ST.find(k)
        if not c:
            out.append(f"{k} (not on this PC any more)")
            continue
        who = "this PC" if c.get("origin") == "local" else f"from {c.get('author') or 'a friend'}"
        out.append(f"{KN.label(c)['name']} ({k}; {who})")
    return ", ".join(out)


def _prompts_words(ids) -> str:
    """The picked scripts / hooks for Claude: "<title> (<id>; yours | <creator>'s)" - read each with
    `tools\\prompts.py show <id>`."""
    out = []
    for i in ids or []:
        try:
            p = PR.get(i)
        except ValueError:
            out.append(f"{i} (not in the library any more)")
            continue
        src = p.get("source") or {}
        whose = f"{src.get('creator') or 'a creator'}'s" if src.get("type") == "creator" else "yours"
        out.append(f"{p.get('title') or PR.auto_title(p.get('text', ''), p.get('kind', ''))} ({i}; {whose})")
    return ", ".join(out)


def describe_request(r: dict) -> str:
    """A request as text for Claude."""
    rows = [("about", r.get("topic")), ("for", r.get("audience")), ("they get", r.get("takeaway")),
            ("the user's angle", r.get("angle")), ("must say", r.get("points")),
            ("length", f"{r['length_s']:g} s" if r.get("length_s") else ""), ("where", WHERE.get(r.get("where") or "", "")),
            ("tone", TONES.get(r.get("tone") or "", "")),
            ("call to action", " - ".join(x for x in (CTAS.get(r.get("cta") or "", ""), r.get("cta_text")) if x)),
            ("language", LANGS.get(r.get("lang") or "", r.get("lang") or "")), ("style like", _videos_words(r.get("like"))),
            ("scripts / hooks like", _prompts_words(r.get("like_prompts"))),
            ("what the user wants", r.get("want")), ("also", r.get("extra"))]
    if r.get("kind") == "title":                         # 0.4.3 *Title & thumbnail first*
        rows = [("about", r.get("topic")), ("for", r.get("viewer")), ("the user's angle", r.get("angle")),
                ("platforms", ", ".join(PLATFORMS.get(x, x) for x in r.get("platforms") or [])),
                ("orientation", ORIENTATIONS.get(r.get("orientation") or "", "")),
                ("language", LANGS.get(r.get("language") or "", r.get("language") or "")),
                ("style like", _videos_words(r.get("style_refs"))),
                ("scripts / hooks like", _prompts_words(r.get("like_prompts"))), ("also", r.get("notes"))]
    if r.get("kind") == "prompt":                        # 2026-10-19: the prompt library's new prompt / Use it, change…
        rows = [("what the user wants", r.get("want")), ("start from", _prompts_words([r["from"]]) if r.get("from") else ""),
                ("change", r.get("change")), ("for", ", ".join(r.get("for") or [])), ("model", r.get("model")),
                ("style like", _videos_words(r.get("style_refs")))]
    head = (f"{r.get('id')} - write a script from zero" if r.get("kind") == "new"
            else f"{r.get('id')} - title & thumbnail first (before filming)" if r.get("kind") == "title"
            else f"{r.get('id')} - a new {r.get('prompt_kind')} prompt" + (f" like {r['from']}" if r.get("from") else "")
            if r.get("kind") == "prompt"
            else f"{r.get('id')} - improve {r.get('script')}" + (
                " - save ONLY your improved script (\"request\": this id, \"made_from\": the script); the app then "
                "replaces the pasted one with it" if r.get("replace") else "")) + f" ({str(r.get('date', ''))[:16]})"
    out = [head] + [f"  {k}: {v}" for k, v in rows if v]
    if r.get("brand"):                                   # 0.6.0: For my brand - My Brand as it was when asked
        from . import brand as BR
        out += ["", "For my brand:", *[f"  {x}" for x in BR.brief_lines(r["brand"], "words")]]
    return "\n".join(out)
