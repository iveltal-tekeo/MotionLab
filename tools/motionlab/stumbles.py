"""Stumbles in a talking take (0.6.0 step 20, docs\\plans.md): what to cut besides the pauses, found in the words
speech to text timed (a *verbatim* transcript - tools\\speech.py transcribe --verbatim - keeps the "um"s that a plain
one tidies away). English and Spanish. Standard library only.

    find(words, lang) -> [{"n", "kind", "t0", "t1", "i0", "i1", "text", "why"}]   (seconds of the take; i0..i1 the
          words, inclusive; n from 1 - the number the user puts one back by)

Kinds: filler ("um", "uh", "eh", "mmm" - never one that ends a question: "eh, Marco?"), repeat (a word or phrase
said twice in a row: "we're going to, we're going to" - one function word only: "the the"; never a run of one word -
"no no no", "very very" is emphasis), stumble (the same with half a word between the copies: "we're go-, we're
going"), retake (a sentence left unfinished and said again right after - its first try and a "sorry" / "wait"
between them; a whole sentence said again; a FINISHED sentence whose ending the next one takes up is rhetoric,
kept), signal (the speaker talks to
the edit: "cut", "again", "let me redo that", "otra vez", "me equivoqué" - that sentence and the one before it).
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

FILLERS = {"en": {"um", "umm", "uh", "uhh", "uhm", "er", "erm", "ah", "ahh", "hmm", "mm", "mmm", "huh"},
           "es": {"eh", "ehh", "em", "emm", "mmm", "mm", "ehm", "este"}}
# a single word repeated is cut only when it is one of these (a function word); "no no", "very very" are emphasis
FUNCTION = {"en": {"i", "a", "an", "the", "to", "and", "of", "in", "on", "it", "is", "we", "you", "that", "this",
                   "my", "so", "but", "if", "for", "with", "im", "its", "were", "theyre", "youre", "at", "be"},
            "es": {"el", "la", "los", "las", "un", "una", "de", "del", "que", "y", "en", "a", "lo", "me", "te", "se",
                   "mi", "es", "por", "para", "con", "como", "al", "su"}}
SIGNALS = {"en": re.compile(r"^(cut|again|one more time|start (over|again)|let me (do|say|start) (that|it|this) "
                            r"(again|over)|let me redo (that|it|this)|(no )?sorry|wait|hold on|scratch that)$"),
           "es": re.compile(r"^(corta|otra vez|de nuevo|repito|me equivoque|me he equivocado|(no )?perdon|espera|"
                            r"vuelvo a empezar|desde el principio)$")}
CONNECT = {"y", "o", "e", "u", "ni", "que", "and", "or"}     # never "half a word" between two copies
SENTENCE_GAP_S = 0.6                 # a pause this long ends a sentence (as . ! ? do)
REPEAT_GAP_S = 1.5                   # two copies further apart than this are not a stumble
RETAKE_WITHIN_S = 12.0               # a retake starts within this after the unfinished try
MAX_PHRASE = 6                       # the longest phrase looked for twice in a row


def norm(w: str) -> str:
    """lower case, no accents, letters and digits only ("¿Qué?" -> "que", "I'm" -> "im")."""
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", "", w)


def _lang(lang: str | None) -> str:
    return "es" if (lang or "").lower().startswith("es") else "en"


def sentences(words: list[dict]) -> list[list[int]]:
    """Word indexes per sentence: one ends at . ! ? or a pause of SENTENCE_GAP_S."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        gap = float(words[i + 1]["t"]) - float(w.get("t1", w["t"])) if i + 1 < len(words) else 99.0
        if re.search(r"[.!?…]$", w["w"]) or gap >= SENTENCE_GAP_S:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def find(words: list[dict], lang: str | None = "en") -> list[dict]:
    """The stumbles in a take's words ([{t, t1, w}] in order) - see the module's docstring."""
    lg = _lang(lang)
    n = len(words)
    N = [norm(w["w"]) for w in words]
    mark: list = [None] * n

    def cut(a: int, b: int, kind: str, why: str) -> None:
        for k in range(a, b + 1):
            if mark[k] is None:
                mark[k] = (kind, why)
    S = sentences(words)
    question = {i for s in S if len(s) <= 4 and re.search(r"\?$", words[s[-1]]["w"]) for i in s}
    # 1. fillers (never in a short question: "eh, ¿Marco?")
    for i, t in enumerate(N):
        raw = words[i]["w"]
        if "?" in raw or "¿" in raw or i in question:
            continue
        if t in FILLERS[lg] and (t != "este" or raw.endswith(("...", "…", ","))):
            cut(i, i, "filler", f"filler \"{raw.strip('.,…')}\"")
    # 2. a phrase said twice in a row (with at most half a word between the copies)
    i = 0
    while i < n:
        done = False
        for L in range(MAX_PHRASE, 0, -1):
            if L > 1 and len(set(N[i:i + L])) == 1:
                continue                                  # "so so so": one word as a run - emphasis
            for k in (0, 1):
                if L == 1 and k and not (i + 1 < n and words[i + 1]["w"].endswith("-")):
                    continue                              # one word + half a word only when it is marked broken
                j = i + L + k
                if j + L > n or not all(N[i:i + L]) or N[i:i + L] != N[j:j + L]:
                    continue
                if float(words[j]["t"]) - float(words[i + L - 1].get("t1", words[i + L - 1]["t"])) > REPEAT_GAP_S:
                    continue
                if re.search(r"[.!?…]$", words[j - 1]["w"]):
                    continue                              # a finished sentence said again: on purpose, kept
                if k:
                    mid = N[i + L]
                    if len(mid) > 3 and not words[i + L]["w"].endswith("-") or mid in CONNECT \
                            or re.search(r"[.,;!?]$", words[i + L]["w"]):
                        continue                          # between the copies only a broken-off half word
                if L == 1 and N[i] not in FUNCTION[lg]:
                    continue                              # "no no", "very very": emphasis
                text = " ".join(w["w"] for w in words[i:j])
                cut(i, j - 1, "stumble" if k else "repeat", ("stumbled and said again: " if k else "said twice: ")
                    + f"\"{text}\"")
                i, done = j, True
                break
            if done:
                break
        if not done:
            i += 1
    # 3. a sentence left unfinished and said again right after (its first try + what is between)
    for a in range(len(S)):
        A = S[a]
        closed = bool(re.search(r"[.!?…]$", words[A[-1]]["w"]))
        for b in range(a + 1, min(a + 3, len(S))):
            B = S[b]
            if float(words[B[0]]["t"]) - float(words[A[-1]].get("t1", words[A[-1]]["t"])) > RETAKE_WITHIN_S:
                break
            if b == a + 2 and len(S[a + 1]) > 4:
                break                                     # between them only a "sorry" / "wait", not a sentence
            nb = [N[k] for k in B]
            at = None
            for p in range(len(A)):
                if closed and p > 0:
                    break                                 # a finished sentence whose ending comes again: rhetoric
                suf = [N[k] for k in A[p:]]
                if len(suf) >= 2:
                    if suf[:2] != nb[:2] or len(nb) < len(suf):
                        continue
                    last = nb[len(suf) - 1]
                    prefix = suf[:-1] == nb[:len(suf) - 1] and last.startswith(suf[-1])
                    open_ = not re.search(r"[.,;!?…]$", words[A[-1]]["w"])
                    alike = len(suf) >= 4 and SequenceMatcher(None, suf, nb[:len(suf)]).ratio() >= 0.85
                    if prefix or (open_ and alike):
                        at = p
                        break
                elif len(A) == 1 and suf[0] and suf[0] == nb[0] and len(B) > 1:
                    at = p                                # a false start: "Today... Today I'll show you"
                    break
            if at is not None:
                end = B[0] - 1
                cut(A[at], end, "retake", "said again right after: \""
                    + " ".join(words[k]["w"] for k in range(A[at], end + 1)) + "\"")
                break
    # 4. the speaker talks to the edit ("wait, cut, again"): those sentences and, unless they are only a "sorry" /
    #    "wait", the try before them (when it ended under 6 s earlier) - the speaker is about to say it again
    sig = [len(A) <= 6 and bool(SIGNALS[lg].search(" ".join(N[k] for k in A).strip())) for A in S]
    a = 0
    while a < len(S):
        if not sig[a]:
            a += 1
            continue
        b = a
        while b + 1 < len(S) and sig[b + 1]:
            b += 1
        said = " ".join(N[k] for s in S[a:b + 1] for k in s)
        soft = all(re.fullmatch(r"(no )?(sorry|perdon)|wait|hold on|espera", " ".join(N[k] for k in s).strip())
                   for s in S[a:b + 1])
        start = S[a][0]
        if a > 0 and not soft and not sig[a - 1] and float(words[S[a][0]]["t"]) - float(
                words[S[a - 1][-1]].get("t1", words[S[a - 1][-1]]["t"])) < 6:
            start = S[a - 1][0]
        cut(start, S[b][-1], "signal", f"said to the edit: \"{said}\"")
        a = b + 1
    return _groups(words, mark)


def _groups(words: list[dict], mark: list) -> list[dict]:
    out, i, n = [], 0, len(words)
    while i < n:
        if mark[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < n and mark[j + 1] is not None and mark[j + 1][0] == mark[i][0]:
            j += 1
        out.append({"n": len(out) + 1, "kind": mark[i][0], "i0": i, "i1": j, "t0": round(float(words[i]["t"]), 3),
                    "t1": round(float(words[j].get("t1", words[j]["t"])), 3),
                    "text": " ".join(w["w"] for w in words[i:j + 1]), "why": mark[i][1]})
        i = j + 1
    return out


def spans(words: list[dict], groups: list[dict], pad_s: float = 0.04) -> list[tuple[float, float] | None]:
    """The time to cut for each group (seconds of the take; one per group, None = no room): from the end of the word
    kept before it (+pad) to the start of the word kept after it (-pad), never into a kept word."""
    out = []
    for g in groups:
        prev_end = float(words[g["i0"] - 1].get("t1", words[g["i0"] - 1]["t"])) if g["i0"] > 0 else 0.0
        nxt = float(words[g["i1"] + 1]["t"]) if g["i1"] + 1 < len(words) else float(
            words[g["i1"]].get("t1", words[g["i1"]]["t"])) + 0.3
        a = max(prev_end + pad_s, g["t0"] - 0.08)
        b = min(nxt - pad_s, g["t1"] + 0.08)
        out.append((round(a, 3), round(b, 3)) if b > a else None)
    return out


def selfcheck(verbose: bool = True) -> dict:
    """Known answers on made-up takes (words with times): each kind found where it is, emphasis and rhetoric kept."""
    lines, ok = [], True

    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + msg)

    def take(text: str, gaps: dict | None = None) -> list[dict]:
        out, t = [], 0.0
        for k, w in enumerate(text.split()):
            t += (gaps or {}).get(k, 0.05)
            out.append({"t": round(t, 3), "t1": round(t + 0.25, 3), "w": w})
            t += 0.25
        return out

    def kinds(text, lang="en", gaps=None):
        ws = take(text, gaps)
        return [(g["kind"], g["text"]) for g in find(ws, lang)]
    got = kinds("So um today we're going to, we're going to look at uh three edits.")
    check(got == [("filler", "um"), ("repeat", "we're going to,"), ("filler", "uh")], f"fillers + a phrase twice: {got}")
    got = kinds("No no no, this is very very important. The the cut lands here.")
    check(got == [("repeat", "The")], f"emphasis kept, a function word twice cut: {got}")
    got = kinds("We're go- we're going to cut it.")
    check(got == [("stumble", "We're go-")], f"half a word between the copies: {got}")
    got = kinds("Today I want to show you Today I want to show you three edits.", gaps={6: 0.9})
    check(got == [("repeat", "Today I want to show you")], f"an unfinished sentence said again: {got}")
    got = kinds("Today I want to show I want to show you three edits.", gaps={5: 2.0})
    check(got == [("retake", "I want to show")], f"... after a longer pause, from where it restarts: {got}")
    got = kinds("Your song sounds good. Your song sounds good, so why should it look worse?", gaps={4: 0.3})
    check(got == [("retake", "Your song sounds good.")], f"a whole sentence said again right after: {got}")
    got = kinds("It all starts with the hook. The hook decides everything.", gaps={6: 0.3})
    check(got == [], f"a finished sentence whose ending the next one takes up (rhetoric) kept: {got}")
    got = kinds("The price is twenty euros wait cut again The price is fifty euros.", gaps={5: 0.8, 6: 0.8, 7: 0.8,
                                                                                           8: 0.8})
    check(got == [("signal", "The price is twenty euros wait cut again")],
          f"the speaker talks to the edit - the try before it goes too: {got}")
    got = kinds("This is the hook. Sorry. The hook comes first.", gaps={4: 0.8, 5: 0.8})
    check(got == [("signal", "Sorry.")], f"a lone 'sorry' goes, the sentence before stays: {got}")
    got = kinds("Eh, ¿Marco? Vamos a ver, vamos a ver cómo, eh, cómo lo hacemos.", "es")
    check(got == [("repeat", "Vamos a ver,"), ("filler", "eh,")], f"Spanish (the question kept): {got}")
    got = kinds("El precio es veinte euros. Me equivoqué. El precio es cincuenta euros.", "es",
                gaps={5: 0.8, 7: 0.8})
    check(got == [("signal", "El precio es veinte euros. Me equivoqué.")], f"Spanish, said to the edit: {got}")
    ws = take("So um today")
    sp = spans(ws, find(ws, "en"))
    check(len(sp) == 1 and sp[0] and ws[0]["t1"] < sp[0][0] < sp[0][1] < ws[2]["t"],
          f"a cut never reaches into the kept words: {sp} between 'So' (ends {ws[0]['t1']}) and 'today' ({ws[2]['t']})")
    lines.append(f"{'PASS' if ok else 'FAIL'}: stumbles")
    if verbose:
        print("\n".join(lines))
    return {"ok": ok, "passed": ok, "lines": lines}
