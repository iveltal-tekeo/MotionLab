"""The app's translations: the check, the merge and the work list per area (2026-10-19; the contract:
tools\\motionlab\\app\\CLAUDE.md "Languages", the mechanism: tools\\motionlab\\i18n.py). Standard library only and
nothing of the lab imported: the code is read as text (a small JavaScript scanner + Python's ast), in a few seconds.

    .venv\\Scripts\\python tools\\dev\\i18n_check.py check [--area <area>] [--lang es]
          every key the code uses (t / ta / tn in app.js, {{t:...}} in index.html, i18n t / tn in Python) has a
          translation; each translation keeps its key's {placeholders} and tags; a count has "one" and "other"; every
          noun plural() is called with is in _nouns; no key the code no longer uses; no local `t` hiding t(); a
          template with ${...} as a key; multi-word translations identical to the English are listed (warnings).
          --area = only that area's code and its part file. Exit 1 = something to fix.
    .venv\\Scripts\\python tools\\dev\\i18n_check.py scan [--list]
          the English texts not wrapped yet, counted: the page (app.js, index.html), the server's words (Python),
          report.html and the Motion Graphics library's labels (by key: done when the catalogue has them)
    .venv\\Scripts\\python tools\\dev\\i18n_check.py todo <area> [--json]
          one area's texts not wrapped yet: file:line, function, kind, the text; for app.js also the places that
          show a label the server sends (wrap them: esc(t(x.label)))
    .venv\\Scripts\\python tools\\dev\\i18n_check.py areas
          every app.js top-level function with its count, and the split into areas of similar size
          -> tools\\dev\\i18n_areas.json (app.js 10 areas, the Python files 3, index.html, report, the library)
    .venv\\Scripts\\python tools\\dev\\i18n_check.py merge [--lang es]
          ui\\i18n\\parts\\es.<area>.json -> ui\\i18n\\es.json (a key two parts translate differently: refused)
    .venv\\Scripts\\python tools\\dev\\i18n_check.py selfcheck
          the scanner and the check on small samples

An area's work: `todo <area>` -> wrap each text in its code (t('...'), tn(n, '{n} video', '{n} videos'), ta() inside
an attribute; sentence pieces glued by + or ?: first become ONE sentence with {placeholders}; a server label shown on
the page: esc(t(x.label))) -> the Spanish into ui\\i18n\\parts\\es.<area>.json only (the glossary: es.core.json
"_meta") -> `check --area <area>`. English stays byte for byte as it was. The page and the server read es.json + every
part file, so a part shows before `merge` folds it in; never edit es.json by hand.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import collections
import html
import json
import re
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[2]
UI = LAB / "tools" / "motionlab" / "app" / "ui"
APPJS, INDEX, CSS_FILE = UI / "app.js", UI / "index.html", UI / "app.css"
I18N_DIR = UI / "i18n"
AREAS_FILE = Path(__file__).resolve().with_name("i18n_areas.json")
REPORT = LAB / "tools" / "motionlab" / "report_html.py"
MOTION = LAB / "tools" / "overlays" / "motion"
# the Python files whose words reach the page (raise messages -> toasts, fields, label tables, job titles ...)
PY_FILES = (["tools/motionlab/app/" + f for f in ("server.py", "data.py", "system.py", "jobs.py", "jobtools.py",
                                                 "updater.py", "report.py", "trash.py", "player.py")]
            + ["tools/motionlab/" + f + ".py" for f in ("thumbsets", "usage", "speech", "upstream", "style", "publish",
                                                       "prompts", "knowledge", "styles", "thumbnail", "taxonomy",
                                                       "script", "profile", "logos", "fonts", "colour", "textsets",
                                                       "editreq")]
            + ["tools/download.py"])
# the user's other Claude window works on these (2026-10-19): their words wait (never edited from here)
WAITS = ["tools/motionlab/templates.py", "tools/motionlab/overlay_settings.py", "tools/motionlab/looks.py",
         "tools/motionlab/template_match.py", "tools/motionlab/template_read.py", "tools/overlay.py",
         "tools/templates.py", "tools/overlays/motion/_looks/"]
# files whose tables are mostly names (brands, fonts) and search words: only these label tables are words to translate
# ("values" = the dict's values are the labels, "keys" = its keys are)
NAMES_ONLY = {"tools/motionlab/logos.py": {"VARIANT_WORDS": "values", "GROUP_WORDS": "values"},
              "tools/motionlab/fonts.py": {"GROUPS": "keys"}}
N_JS_AREAS = 10
PH = ""                                   # one placeholder per ${...}

# ============================================================================================ the JavaScript scanner
KW_BEFORE_EXPR = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw", "instanceof",
                  "yield", "await"}
ID_RE = re.compile(r"[A-Za-z_$][\w$]*")
NUM_RE = re.compile(r"\d[\d_]*(\.\d+)?([eE][+-]?\d+)?|\.\d+")
_ESC = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v"}


def js_cook(raw: str) -> str:
    """A string / template literal's text as JavaScript reads it (escapes decoded)."""
    out, i, n = [], 0, len(raw)
    while i < n:
        c = raw[i]
        if c != "\\" or i + 1 >= n:
            out.append(c)
            i += 1
            continue
        d = raw[i + 1]
        if d in _ESC:
            out.append(_ESC[d]); i += 2
        elif d == "0" and not (i + 2 < n and raw[i + 2].isdigit()):
            out.append("\0"); i += 2
        elif d == "x" and re.fullmatch(r"[0-9a-fA-F]{2}", raw[i + 2:i + 4]):
            out.append(chr(int(raw[i + 2:i + 4], 16))); i += 4
        elif d == "u" and raw[i + 2:i + 3] == "{":
            j = raw.find("}", i)
            out.append(chr(int(raw[i + 3:j], 16))); i = j + 1
        elif d == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", raw[i + 2:i + 6]):
            out.append(chr(int(raw[i + 2:i + 6], 16))); i += 6
        elif d in "\r\n":                           # a line continuation
            i += 3 if raw[i + 1:i + 3] == "\r\n" else 2
        else:
            out.append(d); i += 2
    return "".join(out)


class Scan:
    """Literals of a JS source: strings and templates (a template's text has PH per ${...}; the code inside is scanned
    too), with comments and regexes skipped. kinds[pos]: 0 code, 1 literal text, 2 comment, 3 regex."""

    def __init__(self, src: str):
        self.s, self.n, self.lits, self.comments, self.regexes = src, len(src), [], [], []
        self.lines = [0] + [m.end() for m in re.finditer("\n", src)]
        self.nest = 0
        self.code(0)
        k = bytearray(self.n)
        for L in self.lits:
            k[L["start"]:L["end"]] = b"\x01" * (L["end"] - L["start"])
            for a, b in L.get("exprs", ()):
                k[a:b] = b"\x00" * (b - a)
        for a, b in self.comments:
            k[a:b] = b"\x02" * (b - a)
        for a, b in self.regexes:
            k[a:b] = b"\x03" * (b - a)
        self.kinds = k
        self.by_start = {L["start"]: L for L in self.lits}

    def line(self, pos: int) -> int:
        return bisect.bisect_right(self.lines, pos)

    def code(self, i: int, until_brace: bool = False) -> int:
        s, n, depth, prev = self.s, self.n, 0, "op"
        while i < n:
            c = s[i]
            if c in " \t\r\n":
                i += 1
                continue
            if s.startswith("//", i):
                j = s.find("\n", i)
                j = n if j < 0 else j
                self.comments.append((i, j)); i = j
                continue
            if s.startswith("/*", i):
                j = s.find("*/", i + 2)
                j = n if j < 0 else j + 2
                self.comments.append((i, j)); i = j
                continue
            if c in "'\"":
                i = self.string(i, c); prev = "val"
                continue
            if c == "`":
                i = self.template(i); prev = "val"
                continue
            if c == "/":
                if prev in ("val", "id"):
                    i += 1; prev = "op"
                    continue
                i = self.regex(i); prev = "val"
                continue
            m = ID_RE.match(s, i)
            if m:
                prev = "op" if m.group() in KW_BEFORE_EXPR else "id"; i = m.end()
                continue
            m = NUM_RE.match(s, i)
            if m:
                prev = "val"; i = m.end()
                continue
            if c == "{":
                depth += 1; prev = "op"; i += 1
                continue
            if c == "}":
                if until_brace and depth == 0:
                    return i + 1
                depth -= 1; prev = "val"; i += 1
                continue
            if c in ")]":
                prev = "val"; i += 1
                continue
            prev = "op"; i += 1
        return i

    def string(self, i: int, q: str) -> int:
        s, j = self.s, i + 1
        while j < self.n and s[j] != q:
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == "\n":
                break
            j += 1
        raw = s[i + 1:j]
        self.lits.append({"kind": "str", "start": i, "end": j + 1, "line": self.line(i), "text": js_cook(raw),
                          "nph": 0, "nest": self.nest})
        return j + 1

    def template(self, i: int) -> int:
        s, j, buf, nph, exprs = self.s, i + 1, [], 0, []
        rec = {"kind": "tpl", "start": i, "line": self.line(i), "nest": self.nest}
        self.lits.append(rec)                      # source order: the outer template before its inner ones
        seg = j
        while j < self.n:
            c = s[j]
            if c == "\\":
                j += 2
                continue
            if c == "`":
                buf.append(js_cook(s[seg:j])); j += 1
                break
            if s.startswith("${", j):
                buf.append(js_cook(s[seg:j])); nph += 1; buf.append(PH)
                self.nest += 1
                k = self.code(j + 2, until_brace=True)
                self.nest -= 1
                exprs.append((j + 2, k - 1)); j = seg = k
                continue
            j += 1
        rec.update(end=j, text="".join(buf), nph=nph, exprs=exprs)
        return j

    def regex(self, i: int) -> int:
        s, j, cls = self.s, i + 1, False
        while j < self.n:
            c = s[j]
            if c == "\\":
                j += 2
                continue
            if c == "[":
                cls = True
            elif c == "]":
                cls = False
            elif c == "/" and not cls:
                j += 1
                break
            elif c == "\n":
                break
            j += 1
        while j < self.n and s[j].isalpha():
            j += 1
        self.regexes.append((i, j))
        return j


CALL = re.compile(r"(?<![\w$.])(t|ta|tn)\(")


def split_args(sc: Scan, p: int) -> list[tuple[int, int]]:
    """The top-level arguments of a call whose "(" ends at p: [(start, end)] spans."""
    s, k, depth, out, a = sc.s, sc.kinds, 0, [], p
    while p < sc.n:
        kk = k[p]
        if kk == 1:
            L = sc.by_start.get(p)
            p = L["end"] if L else p + 1
            continue
        if kk:
            p += 1
            continue
        c = s[p]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                out.append((a, p))
                return out
            depth -= 1
        elif c == "," and depth == 0:
            out.append((a, p)); a = p + 1
        p += 1
    return out


def arg_literal(sc: Scan, span: tuple[int, int]):
    a, b = span
    while a < b and sc.s[a].isspace():
        a += 1
    while b > a and sc.s[b - 1].isspace():
        b -= 1
    L = sc.by_start.get(a)
    return L if L and L["end"] == b else None


def js_calls(sc: Scan) -> dict:
    """t / ta / tn calls: keys (literal), the literals they wrap, dynamic calls, keys that are templates with ${}."""
    keys, wrapped, dynamic, bad, ones = {}, set(), [], [], {}
    for m in CALL.finditer(sc.s):
        if sc.kinds[m.start()] != 0 or re.search(r"function\s*$", sc.s[max(0, m.start() - 12):m.start()]):
            continue
        name, args = m.group(1), split_args(sc, m.end())
        idx = [1, 2] if name == "tn" else [0]
        for i in idx:
            if i >= len(args):
                continue
            L = arg_literal(sc, args[i])
            if not L:
                if i == idx[-1]:
                    dynamic.append((sc.line(m.start()), name, sc.s[args[i][0]:args[i][1]].strip()[:60]))
                continue
            wrapped.add(L["start"])
            if L["nph"]:
                bad.append((L["line"], L["text"].replace(PH, "${}")))
                continue
            if i == idx[-1]:
                keys.setdefault(L["text"], []).append(L["line"])
                if name == "tn" and len(args) > 1:
                    one = arg_literal(sc, args[1])
                    ones[L["text"]] = one["text"] if one else None
    return {"keys": keys, "wrapped": wrapped, "dynamic": dynamic, "bad": bad, "ones": ones}


def decls(src: str) -> list[tuple[int, str]]:
    """Top-level declarations (column 0): (line, name), in file order."""
    out = []
    for i, ln in enumerate(src.split("\n"), 1):
        m = re.match(r"^(?:async\s+)?(?:function\s*\*?\s*([\w$]+)|(?:const|let|var)\s+([\w$]+)|class\s+([\w$]+))", ln)
        if m:
            out.append((i, next(g for g in m.groups() if g)))
    return out


def enclosing(table: list[tuple[int, str]], line: int) -> str:
    k = bisect.bisect_right([a for a, _ in table], line) - 1
    return table[k][1] if k >= 0 else "(top)"


def sections(src: str) -> list[tuple[int, str]]:
    return [(i, m.group(1).strip()) for i, ln in enumerate(src.split("\n"), 1)
            if (m := re.match(r"^// =+ (.+)$", ln))]


# ---- which literals are words for the user (the assessment's scanner, 2026-10-18: ~97 % right on a sample)
TAG = re.compile(r"<(/?)([A-Za-z][\w-]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*)>|<!--.*?-->", re.S)
VIS_ATTR = re.compile(r"\b(title|placeholder|alt|aria-label|label|data-tip)\s*=\s*(\"([^\"]*)\"|'([^']*)')")
LOOKS_HTML = re.compile(r"<(/?)[A-Za-z][\w-]*(\s|>|/>|" + PH + r")|&[a-z]+;|&#\d+;")
INLINE = {"b", "i", "em", "strong", "a", "code", "kbd", "small", "u", "mark", "sup", "sub", "br", "abbr", "wbr", "s", "q"}
WORD = re.compile(r"[A-Za-z]{2,}")
LABEL_UPPER = {"OK", "SFX", "PASS", "WARN", "FAIL", "SKIP", "OPTIONAL", "NEW"}
_CSS: set | None = None


def css_classes() -> set:
    global _CSS
    if _CSS is None:
        _CSS = set(re.findall(r"\.([A-Za-z_][\w-]*)", CSS_FILE.read_text(encoding="utf-8"))) if CSS_FILE.exists() else set()
    return _CSS


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def readable(t: str) -> bool:
    return bool(WORD.search(re.sub(r"<[^>]*>", " ", t.replace(PH, " "))))


def plain_kind(t: str, before: str, after: str) -> str:
    """'ui' | why not: selector, class, id, path, css, code, a Claude command / prompt, a key ..."""
    bare, withx = t.replace(PH, "").strip(), t.replace(PH, "X").strip()
    nwords = len(re.findall(r"[A-Za-z]{2,}", withx))
    b = before[-80:]
    if not bare or not WORD.search(bare):
        return "nowords"
    if re.search(r"(claudeBtn|openClaude|launchClaude)\(\s*$", b) or re.search(r"\b(prompt|cmd|command)\s*[:=]\s*$", b) \
            or re.search(r"(?:const|let)\s+[A-Z_]*(?:PROMPT|CMD|INCOMING|COMMAND)[A-Z_]*\s*=\s*$", b):
        return "claude-cmd" if re.match(r"^/[a-z][a-z-]+", withx) else "claude-prompt"
    if re.match(r"^/[a-z][a-z-]+( |$)", withx) and not withx.startswith(("/api/", "/files/", "/ui/")):
        return "claude-cmd"
    if re.match(r"\s*:(?!:)", after) and re.search(r"[{,]\s*$", b):
        return "objkey"                                    # {'Hard cut': '#e9e9ec'}: a key, not a word shown
    if re.search(r"\.join\(\s*$", b):
        return "ui" if nwords else "nowords"               # ' and ', ' or '
    if re.search(r"(\$\$?|querySelector(All)?|getElementById|closest|matches)\(\s*$", b):
        return "selector"
    if re.search(r"(classList\.(add|remove|toggle|contains)|className\s*[+]?=|addEventListener|removeEventListener|"
                 r"localStorage\.(get|set|remove)Item|dataset\.\w+\s*===?|\.setAttribute|\.getAttribute|"
                 r"\.style\.\w+\s*=|cssText\s*=|createElement|new RegExp|\.(split|replace|startsWith|endsWith|includes|"
                 r"indexOf|test|match)\()\s*$", b):
        return "code-arg"
    if re.search(r"(api|fetch|fileUrl|openPath|location\.hash\s*=|href\s*=)\(?\s*$", b):
        return "route"
    if re.search(r"(===?|!==?|case)\s*$", b) or re.match(r"\s*(===?|!==?)", after):
        return "compare"
    if re.match(r"^[.#\[]|.*\[data-|.*:(checked|hover|focus|not\()", bare):
        return "selector"
    if re.match(r"^(/api/|/files/|/ui/|#/|https?:|\.\./|\?\w+=)", withx) or "/api/" in withx \
            or (re.search(r"\\[A-Za-z]", withx) and " " not in withx) \
            or re.match(r"^[\w.\-]+\.(json|md|png|jpg|jpeg|mp4|mov|txt|html|css|js|cube|srt|vtt|wav|mp3|svg|docx|pdf)$", bare) \
            or (re.match(r"^[\w{}X./\-]*/[\w{}X./\-]*$", withx) and " " not in withx):
        return "path"
    if re.match(r"^\(?[a-z-]+\s*:\s*[^;:]+\)?;?\s*$", bare) and not re.search(r"[A-Za-z]{2,}\s+[A-Za-z]{2,}\s+[A-Za-z]", bare) \
            or re.match(r"^([a-z-]+\s*:\s*[^;:]+;\s*)+$", bare):
        return "css"
    if re.match(r"^\s*(data-[\w-]+|tabindex|checked|selected|disabled|hidden|type|name|value|style|class|id)\b", t) \
            and re.match(r"^\s*[\w-]+(=\"[^\"]*\")?\s*$", withx):
        return "attr"
    toks = bare.split()
    if toks and all(x in css_classes() for x in toks):
        return "class"
    if re.match(r"^[a-z0-9_\-:./@]+$", bare):             # one lowercase token: an id, a kind, an event, a type...
        if re.search(r"plural\(\s*[^,()]+(\([^()]*\))?\s*,\s*$", b):
            return "noun"                                  # plural(n, 'video'): its forms live in _nouns
        if PH in t and re.search(r"[a-z]{2,}:?\s+X|X\s+[a-z]{2,}", withx) and not re.match(r"^\s*-", t) and "=" not in t:
            return "ui"                                    # 'today {}', 'saved {}'
        if re.match(r"^(s|es)$", bare) and re.search(r"[?:]\s*$", b):
            return "plural-suffix"
        return "id"
    if bare in LABEL_UPPER:
        return "ui"
    if re.match(r"^[A-Z][A-Za-z]*(Left|Right|Up|Down)$|^(Enter|Escape|Space|Tab|Backspace|Home|End|PageUp|PageDown)$", bare) \
            and re.search(r"key", b):
        return "key"
    if re.match(r"^[A-Z][A-Z0-9_.-]+$", bare):
        return "upper"
    if re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+", bare) or re.match(r"^[\"'\]\s]*\]", bare):
        return "code"                                      # IntersectionObserver, YouTube; '"] .vbtn' (a selector's end)
    if re.match(r"^[\w-]+(/[\w-]+)+$", bare) or re.match(r"^\w+/[\w.+-]+;", bare):
        return "mime"
    if re.search(r"=>|[;{}]\s*$|\bfunction\b|document\.|window\.", bare):
        return "code"
    return "ui"


def html_messages(t: str) -> list[tuple[str, str]]:
    """The text messages (text nodes merged across inline tags) + visible attributes of an HTML-ish literal."""
    t2 = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t2 = re.sub(r"<[A-Za-z][^<>]*$", " ", t2)              # a tag the next piece of code finishes: not text
    out, buf = [], []

    def flush():
        txt = "".join(buf)
        if readable(html.unescape(txt)):                   # "&times;" is a sign, not the word "times"
            txt = re.sub(r"^(\s|<[^>]*>)+", "", txt)
            txt = re.sub(r"(\s|<[^>]*>)+$", "", txt)
            out.append(("text", norm(txt)))
        buf.clear()

    pos = 0
    for m in TAG.finditer(t2):
        buf.append(t2[pos:m.start()])
        if (m.group(2) or "").lower() in INLINE:
            buf.append(m.group(0))
        else:
            flush()
        for a in VIS_ATTR.finditer(m.group(0)):
            v = a.group(3) if a.group(3) is not None else a.group(4)
            if readable(v):
                out.append(("attr:" + a.group(1), norm(v)))
        pos = m.end()
    seg = t2[pos:]
    if re.match(r"^[^<>\"]*\"\s*>", seg):                # the end of a tag split across literals: not text
        seg = seg[seg.index(">") + 1:]
    buf.append(seg)
    flush()
    return out


def lit_messages(L: dict, code: str) -> tuple[list[tuple[str, str]], str]:
    t = L["text"]
    before = code[max(0, L["start"] - 100):L["start"]]
    after = code[L["end"]:L["end"] + 20]
    if LOOKS_HTML.search(t) or (re.search(r"<(/?)[A-Za-z][\w-]*", t) and ">" in t):
        return html_messages(t), "html"
    k = plain_kind(t, before, after)
    return ([("plain", norm(t))] if k == "ui" else []), k


def code_text(sc: Scan) -> str:
    """The source with comments blanked (same length): the context the classifier reads."""
    s = list(sc.s)
    for a, b in sc.comments:
        for i in range(a, b):
            if s[i] != "\n":
                s[i] = " "
    return "".join(s)


def js_report(src: str | None = None, file: str = "app.js") -> dict:
    """app.js: the keys it uses, the texts not wrapped yet (per top-level function), plural()'s nouns, the label
    sites, the local t / tn / ta names that would hide the helpers."""
    src = APPJS.read_text(encoding="utf-8") if src is None else src
    sc = Scan(src)
    code = code_text(sc)
    calls = js_calls(sc)
    table = decls(src)
    msgs = []
    for L in sc.lits:
        if L["start"] in calls["wrapped"]:
            continue
        ms, why = lit_messages(L, code)
        for kind, text in ms:
            msgs.append({"file": file, "line": L["line"], "fn": enclosing(table, L["line"]), "kind": kind,
                         "text": text.replace(PH, "{}")})
    # plural(n, 'noun') (and the wrappers that pass a noun on: n(x, 'cut')), the ?: nouns inside its argument
    nouns = collections.defaultdict(list)
    wrappers = set(re.findall(r"\b(\w+)\s*=\s*\(\s*\w+\s*,\s*(\w+)\s*\)\s*=>[^\n;]*?plural\([^,]+,\s*\2\s*\)", code))
    names = {"plural"} | {w for w, _ in wrappers}
    for m in re.finditer(r"(?<![\w$.])(" + "|".join(sorted(names)) + r")\(", code):
        if sc.kinds[m.start()] != 0:
            continue
        args = split_args(sc, m.end())
        if len(args) < 2:
            continue
        a, b = args[1]
        lits = [L for L in sc.lits if a <= L["start"] < b and L["kind"] == "str"]
        for L in lits:
            before = code[max(0, L["start"] - 3):L["start"]]
            if L["start"] == a + len(sc.s[a:b]) - len(sc.s[a:b].lstrip()) or re.search(r"[?:]\s*$", before):
                nouns[L["text"]].append(L["line"])
    # the places that show a label the server sends: esc(x.label) ... (wrap: esc(t(x.label)))
    labels = []
    for m in re.finditer(r"\besc\(\s*([\w$]+(?:\.[\w$]+|\[[^\]]+\])*\.(label|how|help|hint|need|what|words|step|why|"
                         r"text_words))\s*\)", code):
        if sc.kinds[m.start()] == 0:                       # code (a template's ${...} counts as code)
            ln = sc.line(m.start())
            labels.append({"file": file, "line": ln, "fn": enclosing(table, ln), "kind": "label", "text": m.group(0)})
    # numbers shown with fixed decimals: x.toFixed(d) -> dec(x, d) (Spanish 4,5); CSS (style="...") and values sent
    # to the server keep toFixed
    numbers = []
    for m in re.finditer(r"\.toFixed\(", code):
        ln = sc.line(m.start())
        fn = enclosing(table, ln)
        if sc.kinds[m.start()] != 0 or fn in ("dec", "compactNum") or \
                re.search(r'style="[^"]*$', code[max(0, m.start() - 200):m.start()]):
            continue
        a = code.rfind("\n", 0, m.start()) + 1
        numbers.append({"file": file, "line": ln, "fn": fn, "kind": "number",
                        "text": "dec(x, d) for: " + code[max(a, m.start() - 70):m.end() + 4].strip()})
    # a local t / tn / ta in a function that calls t(): the call would hit the local name
    shadow = []
    bounds = [a for a, _ in table] + [len(src.split("\n")) + 1]
    lines = code.split("\n")
    for (start, name), end in zip(table, bounds[1:]):
        body = "\n".join(lines[start - 1:end - 1])
        local = set(re.findall(r"(?:\b(?:const|let|var)\s+|[(,]\s*|\bcatch\s*\(\s*)(t|tn|ta)\b(?=\s*(?:=(?!=)|,|\)|=>))",
                               body)) | set(re.findall(r"(?<![\w$.])(t|tn|ta)\s*=>", body))
        if name in ("t", "tn", "ta"):
            continue
        used = {x for x in ("t", "tn", "ta") if re.search(r"(?<![\w$.])" + x + r"\(", body)}
        for x in sorted(local & used):
            shadow.append({"fn": name, "line": start, "name": x})
    dynamic = [d for d in calls["dynamic"] if enclosing(table, d[0]) not in ("t", "tn", "ta")]   # not the helpers
    return {"keys": calls["keys"], "ones": calls["ones"], "dynamic": dynamic, "bad": calls["bad"],
            "msgs": msgs, "nouns": dict(nouns), "labels": labels, "numbers": numbers, "shadow": shadow,
            "decls": table, "sections": sections(src)}


# ============================================================================================ index.html
def index_report() -> dict:
    src = INDEX.read_text(encoding="utf-8")
    keys = {}
    for m in re.finditer(r"\{\{t:(.+?)\}\}", src, re.S):          # the key = the text as shown (motionlab.i18n.fill_html)
        keys.setdefault(html.unescape(m.group(1)), []).append(src.count("\n", 0, m.start()) + 1)
    body = re.sub(r"\{\{t:.+?\}\}", PH, src, flags=re.S)
    body = re.sub(r"<svg\b.*?</svg>", " ", body, flags=re.S)
    body = re.sub(r"<head\b.*?</head>", " ", body, flags=re.S)
    msgs = [{"file": "index.html", "line": 0, "fn": "index.html", "kind": k, "text": t.replace(PH, "{}")}
            for k, t in html_messages(body) if "{{" not in t]
    return {"keys": keys, "msgs": msgs}


# ============================================================================================ Python
UI_KEYS = {"error", "title", "label", "what", "hint", "note", "detail", "text", "message", "msg", "reason", "warn",
           "warning", "help", "tip", "say", "words", "desc", "description", "summary", "step", "line", "why",
           "question", "ask", "example", "feel", "look", "advice", "fix", "how", "need"}
PRINT_FUNCS = {"print", "log", "_log", "say", "warn", "info", "debug", "write", "emit", "out", "log_error"}


def words_in(s: str) -> list[str]:
    return re.findall(r"[A-Za-z]{2,}", s)


def is_text(s: str) -> bool:
    s = s.strip()
    if not words_in(s):
        return False
    if re.match(r"^[a-z0-9_\-:./@*]+$", s) or re.search(r"[\\^$]\w|\(\?|\[\^|\\d|\\s", s):
        return False
    if re.match(r"^[\w./\\-]+\.(json|md|png|jpg|mp4|mov|txt|html|css|js|py|cube|srt|vtt|wav|mp3|svg|log|cmd|bat)$", s):
        return False
    if re.match(r"^(--?[\w-]+|https?://\S+|/api/\S*|%\w)$", s) or re.match(r"^[A-Z][A-Z0-9_]+$", s):
        return False
    if re.match(r"^#[0-9a-fA-F]{3,8}$", s) or not words_in(re.sub(r"<[^>]*>|<[A-Za-z/][^<>]*$", " ", s)):
        return False                                       # a colour, a tag (or a tag's start) with no words outside
    return True


def _fstr(node) -> tuple[str, int]:
    parts, nph = [], 0
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        else:
            parts.append("{}"); nph += 1
    return "".join(parts), nph


def py_report(rel: str, src: str | None = None) -> dict:
    """A Python file: the i18n keys it uses, the words not wrapped yet (raise / field / other), its table strings, and
    every string constant (a key the page translates "by key" is used when some file has it)."""
    src = (LAB / rel).read_text(encoding="utf-8") if src is None else src
    tree = ast.parse(src)
    parent = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parent[c] = p
    alias, bare = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            for a in n.names:
                if a.name == "i18n" and (mod in ("motionlab", "") or mod.endswith(".motionlab")):
                    alias.add(a.asname or a.name)          # from motionlab import i18n as I18N / from .. import i18n
                if (mod == "i18n" or mod.endswith(".i18n")) and a.name in ("t", "tn"):
                    bare.add(a.asname or a.name)           # from motionlab.i18n import t, tn
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.endswith("i18n"):
                    alias.add(a.asname or a.name.split(".")[-1])
    keys, wrapped, bad, ones = {}, set(), [], {}
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nm = f.id if isinstance(f, ast.Name) and f.id in bare else \
            f.attr if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in alias \
            and f.attr in ("t", "tn") else None
        if nm not in ("t", "tn"):
            continue
        idx = [1, 2] if nm == "tn" else [0]
        for i in idx:
            if i >= len(n.args):
                continue
            a = n.args[i]
            for sub in ast.walk(a):
                wrapped.add(sub)
            if isinstance(a, ast.JoinedStr):
                bad.append((a.lineno, _fstr(a)[0]))
            elif isinstance(a, ast.Constant) and isinstance(a.value, str) and i == idx[-1]:
                keys.setdefault(a.value, []).append(a.lineno)
                if nm == "tn" and isinstance(n.args[1], ast.Constant):
                    ones[a.value] = n.args[1].value
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            b0 = n.body[0]
            if isinstance(b0, ast.Expr) and isinstance(b0.value, ast.Constant) and isinstance(b0.value.value, str):
                docs.add(b0.value)
    inner = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            for v in n.values:
                inner.add(v)
                if isinstance(v, ast.FormattedValue) and v.format_spec is not None:
                    inner.add(v.format_spec)
    msgs, consts = [], set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if n in docs or n in inner:
                continue
            text, nph = n.value, 0
            consts.add(text)
        elif isinstance(n, ast.JoinedStr):
            if n in inner:
                continue
            text, nph = _fstr(n)
        else:
            continue
        if n in wrapped or not is_text(text):
            continue
        bucket, a, child, table_name, table_node = "other", parent.get(n), n, "", None
        while a is not None:
            if isinstance(a, ast.Raise):
                bucket = "raise"; break
            if isinstance(a, ast.Call):
                f = a.func
                fname = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ""
                if fname in PRINT_FUNCS:
                    bucket = "print"; break
                if fname in ("compile", "search", "match", "sub", "findall", "fullmatch", "split", "finditer") and \
                        isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "re":
                    bucket = "regex"; break
                if fname in ("get", "setdefault", "pop") and child in a.args[:1]:
                    bucket = "key"; break
                if fname in ("run", "Popen", "check_output", "call", "tool", "add_argument", "add_parser",
                             "ArgumentParser") or fname.startswith("_run"):
                    bucket = "cmd"; break
            if isinstance(a, ast.Dict):
                for k, v in zip(a.keys, a.values):
                    if v is child and isinstance(k, ast.Constant) and k.value in UI_KEYS:
                        bucket = "field"; break
                if bucket == "field":
                    break
            if isinstance(a, ast.keyword) and a.arg in UI_KEYS:
                bucket = "field"; break
            if isinstance(a, ast.Subscript) and child is a.slice or isinstance(a, ast.Compare):
                bucket = "key"; break
            if isinstance(a, (ast.Assign, ast.AnnAssign)) and parent.get(a) is tree:
                tgts = a.targets if isinstance(a, ast.Assign) else [a.target]
                names = [x.id for x in tgts if isinstance(x, ast.Name) and re.match(r"^_?[A-Z][A-Z0-9_]+$", x.id)]
                if names:
                    bucket, table_name, table_node = "table", names[0], a.value; break
            if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                break
            child, a = a, parent.get(a)
        if bucket in ("regex", "key", "cmd", "print"):
            continue
        if rel in NAMES_ONLY and bucket in ("table", "other"):    # only the label tables NAMES_ONLY names
            side, p = NAMES_ONLY[rel].get(table_name) if bucket == "table" else None, parent.get(n)
            if not (side and p is table_node and isinstance(p, ast.Dict)
                    and any(x is n for x in (p.keys if side == "keys" else p.values))):
                continue                                   # brand / font names, search words, colours, CSS
        if bucket == "other" and len(words_in(text)) < 2 and not re.match(r"^[A-Z][a-z]+$", text.strip()):
            continue
        fn, top, a = "", "", parent.get(n)
        while a is not None:
            if isinstance(a, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn = fn or a.name
                top = a.name
            a = parent.get(a)
        if re.search(r"selfcheck|self_check|_selftest|^main$|^_cli|^cli_|^cmd_|_main$|^usage$", top or fn or ""):
            continue                                       # the self-checks and the command line stay English
        msgs.append({"file": rel, "line": n.lineno, "fn": fn or "(module)", "kind": bucket,
                     "text": text, "nph": nph})
    return {"keys": keys, "ones": ones, "bad": bad, "msgs": msgs, "consts": consts}


# ============================================================================================ report + the library
# the MOTIONLAB FEEDBACK export that report.html's script builds (tools\\feedback.py parses it): never translated
EXPORT_TEXT = re.compile(r"^\s*(MOTIONLAB FEEDBACK|---|\|)|^\((no verdict|all hard cuts|none\))")
ATTRS_ONLY = re.compile(r"""^\s*([\w-]+=('[^']*'|"[^"]*"|[^\s'"<>]+)\s*)+$""")       # " class='fa' style='...'"


def report_report() -> dict:
    """report.html's own words (motionlab\\report_html.py): its Python strings and the page script inside it -
    not its docstrings, not the MOTIONLAB FEEDBACK export the script builds."""
    rel = REPORT.relative_to(LAB).as_posix()
    tree = ast.parse(REPORT.read_text(encoding="utf-8"))
    skip = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and \
                isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant):
            skip.add(n.body[0].value)                      # a docstring
        elif isinstance(n, ast.JoinedStr):
            skip.update(n.values)                          # an f-string's pieces: read as the whole f-string
    msgs = []
    for n in ast.walk(tree):
        if n in skip or not (isinstance(n, ast.Constant) and isinstance(n.value, str) or isinstance(n, ast.JoinedStr)):
            continue
        text = n.value if isinstance(n, ast.Constant) else _fstr(n)[0]
        if len(text) > 400 and ("function" in text or "=>" in text):          # the page's script: scan it as JS
            r = js_report(text, file=rel)
            msgs += [{**m, "line": n.lineno + m["line"] - 1, "fn": "JS " + m["fn"]} for m in r["msgs"]
                     if not EXPORT_TEXT.search(m["text"])]
            continue
        if LOOKS_HTML.search(text.replace("{}", PH)):
            msgs += [{"file": rel, "line": n.lineno, "fn": "render", "kind": k, "text": t.replace(PH, "{}")}
                     for k, t in html_messages(text.replace("{}", PH)) if not ATTRS_ONLY.match(t)]
        elif is_text(text) and len(words_in(text)) >= 2 and not re.search(r"[{};]\s*$|^\s*[.#@]", text) \
                and not ATTRS_ONLY.match(text):
            msgs.append({"file": rel, "line": n.lineno, "fn": "render", "kind": "plain", "text": text})
    return {"msgs": msgs}


def motion_texts() -> list[dict]:
    """The Motion Graphics library's words the page shows (translated on the page by key - its files never change):
    each template's name and what, every setting's and option's label."""
    out = []
    if not MOTION.is_dir():
        return out
    for d in sorted(p for p in MOTION.iterdir() if p.is_dir() and not p.name.startswith("_")):
        tj = d / "template.json"
        if tj.is_file():
            try:
                j = json.loads(tj.read_text(encoding="utf-8"))
            except ValueError:
                j = {}
            for k in ("name", "what"):
                if isinstance(j.get(k), str) and j[k].strip():
                    out.append({"file": tj.relative_to(LAB).as_posix(), "line": 0, "fn": d.name, "kind": k,
                                "text": j[k]})
        ih = d / "index.html"
        if ih.is_file():
            h = ih.read_text(encoding="utf-8")
            for m in re.finditer(r'"label"\s*:\s*"((?:[^"\\]|\\.)*)"', h):
                out.append({"file": ih.relative_to(LAB).as_posix(), "line": h.count("\n", 0, m.start()) + 1,
                            "fn": d.name, "kind": "label", "text": json.loads('"' + m.group(1) + '"')})
    return out


# ============================================================================================ the catalogue
def part_files(lang: str) -> list[Path]:
    return sorted((I18N_DIR / "parts").glob(f"{lang}.*.json"))


def load_json(p: Path, errors: list) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError("not an object")
        return d
    except (OSError, ValueError) as e:
        errors.append(f"{p.relative_to(LAB)}: not valid JSON - {e}")
        return {}


def merge_parts(lang: str, errors: list) -> tuple[dict, list[str]]:
    """Every part of a language in one catalogue (as motionlab.i18n.merge_into, sorted); the clashes."""
    cat, clashes, seen = {}, [], {}
    for p in part_files(lang):
        part = load_json(p, errors)
        for k, v in part.items():
            if k.startswith("_"):
                continue
            if k in seen and cat[k] != v:
                clashes.append(f"{k!r}: {seen[k]} and {p.name} translate it differently")
            seen.setdefault(k, p.name)
            cat[k] = v
        for sect in ("_nouns", "_meta"):
            for nk, nv in (part.get(sect) or {}).items():
                have = cat.setdefault(sect, {})
                if nk in have and have[nk] != nv and not (isinstance(nv, dict) and isinstance(have[nk], dict)):
                    clashes.append(f"{sect}.{nk}: two parts give it differently ({p.name})")
                have[nk] = {**have[nk], **nv} if isinstance(nv, dict) and isinstance(have.get(nk), dict) else nv
        if part.get("_by_key"):
            cat["_by_key"] = sorted(set(cat.get("_by_key") or []) | set(part["_by_key"]))
    out = {k: cat[k] for k in ("_meta", "_nouns", "_by_key") if k in cat}
    if "_nouns" in out:
        out["_nouns"] = dict(sorted(out["_nouns"].items(), key=lambda kv: kv[0].lower()))
    out.update(sorted(((k, v) for k, v in cat.items() if not k.startswith("_")), key=lambda kv: (kv[0].lower(), kv[0])))
    return out, clashes


def catalogue(lang: str, errors: list) -> dict:
    """What the app reads: <lang>.json with the parts laid over it."""
    base = I18N_DIR / f"{lang}.json"
    cat = load_json(base, errors) if base.exists() else {}
    merged, _ = merge_parts(lang, errors)
    for k, v in merged.items():
        if k in ("_nouns", "_meta") and isinstance(v, dict):
            cat[k] = {**(cat.get(k) or {}), **v}
        else:
            cat[k] = v
    return cat


VAR = re.compile(r"\{(\w+)\}")
TAGS = re.compile(r"</?[A-Za-z][^<>]*>")


def forms(v) -> list[tuple[str, str]]:
    if isinstance(v, dict):
        return [(k, x) for k, x in v.items() if isinstance(x, str)]
    return [("", v)] if isinstance(v, str) else []


def entry_problems(key: str, v, keep: set) -> tuple[list[str], list[str]]:
    """(errors, warnings) of one translation against its key."""
    errs, warns = [], []
    en_vars, en_tags = set(VAR.findall(key)), sorted(re.sub(r"\s+", " ", x) for x in TAGS.findall(key))
    if isinstance(v, dict):
        if not isinstance(v.get("other"), str) or not isinstance(v.get("one"), str):
            errs.append(f"{key!r}: a count needs \"one\" and \"other\"")
        if set(v) - {"one", "other", "many"}:
            errs.append(f"{key!r}: forms are one / other (/ many), not {sorted(set(v) - {'one', 'other', 'many'})}")
    elif not isinstance(v, str):
        errs.append(f"{key!r}: the translation must be a text or {{\"one\", \"other\"}}")
        return errs, warns
    for form, s in forms(v):
        if not s.strip():
            errs.append(f"{key!r}: empty translation")
            continue
        sv = set(VAR.findall(s))
        if sv - en_vars:
            errs.append(f"{key!r}{' ' + form if form else ''}: {{{', '.join(sorted(sv - en_vars))}}} is not in the English")
        miss = en_vars - sv - ({"n"} if form == "one" else set())
        if miss:
            errs.append(f"{key!r}{' ' + form if form else ''}: loses {{{', '.join(sorted(miss))}}}")
        if sorted(re.sub(r"\s+", " ", x) for x in TAGS.findall(s)) != en_tags:
            errs.append(f"{key!r}{' ' + form if form else ''}: the tags differ from the English ({' '.join(en_tags) or 'none'})")
        en = re.sub(r"\|[a-z][a-z0-9 _-]{0,40}$", "", key)
        if s == en and len(words_in(en)) > 1 and en not in keep:
            warns.append(f"{key!r}: the translation is the English word for word")
    return errs, warns


def area_map() -> dict:
    return json.loads(AREAS_FILE.read_text(encoding="utf-8")) if AREAS_FILE.exists() else {}


def area_of_fn(amap: dict, table: list[tuple[int, str]]) -> dict:
    """app.js function -> its area; a function the areas file does not name (new since) takes the area of the one
    above it."""
    named = {fn: a for a, fns in (amap.get("app.js") or {}).items() for fn in fns}
    out, cur = {}, None
    for _, fn in table:
        cur = named.get(fn, cur)
        out[fn] = cur
    out["(top)"] = next(iter((amap.get("app.js") or {}).keys()), None)
    return out


def area_group(amap: dict, area: str) -> str | None:
    for grp, areas in amap.items():
        if not grp.startswith("_") and isinstance(areas, dict) and area in areas:
            return grp
    return None


def gather(lang: str = "es") -> dict:
    js = js_report()
    ix = index_report()
    py = {rel: py_report(rel) for rel in PY_FILES if (LAB / rel).is_file()}
    rp = report_report() if REPORT.is_file() else {"msgs": []}
    mo = motion_texts()
    errors: list = []
    cat = catalogue(lang, errors)
    return {"js": js, "index": ix, "py": py, "report": rp, "motion": mo, "cat": cat, "load_errors": errors}


def todo_items(G: dict, area: str) -> list[dict]:
    amap = area_map()
    grp = area_group(amap, area)
    cat = G["cat"]
    if grp is None:
        raise SystemExit(f"no area {area!r} - see {AREAS_FILE.relative_to(LAB)} (run: i18n_check.py areas)")
    if grp == "app.js":
        fa = area_of_fn(amap, G["js"]["decls"])
        return [m for m in G["js"]["msgs"] + G["js"]["labels"] + G["js"]["numbers"] if fa.get(m["fn"]) == area]
    if grp == "python":
        files = set(amap["python"][area])
        out = []
        for rel in sorted(files):
            for m in (G["py"].get(rel) or {}).get("msgs", []):
                if m["kind"] == "table" and m["text"] in cat:
                    continue                               # translated on the page by key: done
                out.append(m)
        return out
    if grp == "index.html":
        return G["index"]["msgs"]
    if grp == "report_html.py":
        return G["report"]["msgs"]
    if grp == "motion":
        return [m for m in G["motion"] if m["text"] not in cat]
    return []


# ============================================================================================ commands
def cmd_check(area: str | None, lang: str) -> int:
    G = gather(lang)
    cat, errs, warns = G["cat"], list(G["load_errors"]), []
    meta = cat.get("_meta") or {}
    keep = set(meta.get("keep") or []) | {k for k, v in (meta.get("glossary") or {}).items() if k == v}
    js, ix = G["js"], G["index"]
    used: dict[str, list[str]] = collections.defaultdict(list)
    for k, lines in js["keys"].items():
        used[k] += [f"app.js:{x}" for x in lines]
    for k, lines in ix["keys"].items():
        used[k] += [f"index.html:{x}" for x in lines]
    for rel, r in G["py"].items():
        for k, lines in r["keys"].items():
            used[k] += [f"{rel}:{x}" for x in lines]
    by_data = set()                                       # words the page may look up by key (server labels, library)
    for r in G["py"].values():
        by_data |= r["consts"]
    by_data |= {m["text"] for m in G["motion"]} | {m["text"] for m in G["report"]["msgs"]}
    by_data |= {str(x) for x in cat.get("_by_key") or []}  # a part's own list: keys looked up from other data
    amap = area_map() if area else {}
    part = None
    if area:
        grp = area_group(amap, area)
        if grp is None and area != "core":
            print(f"no area {area!r} in {AREAS_FILE.relative_to(LAB)}")
            return 1
        pf = I18N_DIR / "parts" / f"{lang}.{area}.json"
        part = load_json(pf, errs) if pf.exists() else {}
        if not pf.exists():
            warns.append(f"{pf.relative_to(LAB)} does not exist yet")
        mine: set = set()
        if grp == "app.js":
            fa = area_of_fn(amap, js["decls"])
            table = js["decls"]
            for k, lines in js["keys"].items():
                if any(fa.get(enclosing(table, x)) == area for x in lines):
                    mine.add(k)
        elif grp == "python":
            for rel in amap["python"][area]:
                mine |= set((G["py"].get(rel) or {}).get("keys", {}))
        elif grp == "index.html":
            mine |= set(ix["keys"])
        scope_keys = mine | {k for k in part if not k.startswith("_")}
    else:
        scope_keys = set(used) | {k for k in cat if not k.startswith("_")}
    # 1. every key used has a translation
    for k in sorted(set(used) & scope_keys):
        v = cat.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            errs.append(f"no translation for {k!r} ({', '.join(used[k][:3])})")
    # 2. each translation keeps the key's placeholders / tags; counts have their forms
    entries = part if part is not None else cat
    for k, v in entries.items():
        if k.startswith("_"):
            continue
        e, w = entry_problems(k, v, keep)
        errs += e; warns += w
    tn_keys = set(js["ones"]) | {k for r in G["py"].values() for k in r["ones"]}
    for k in sorted(tn_keys & scope_keys):
        if k in cat and not isinstance(cat[k], dict):
            warns.append(f"{k!r} is a count (tn) - give it {{\"one\": ..., \"other\": ...}}")
    # 3. no key the code no longer uses
    for k in sorted(k for k in entries if not k.startswith("_")):
        if k not in used and k not in by_data:
            errs.append(f"unused key {k!r} - the code no longer has it (reworded? remove or rename it; a key the page "
                        f"looks up from data this check cannot see: list it in the part's \"_by_key\")")
    # 4. plural()'s nouns
    nouns = cat.get("_nouns") or {}
    table = js["decls"]
    fa = area_of_fn(amap, table) if area else {}
    for w, lines in sorted(js["nouns"].items()):
        if area and not any(fa.get(enclosing(table, x)) == area for x in lines):
            continue
        f = nouns.get(w)
        if not (isinstance(f, list) and len(f) == 2 and all(isinstance(x, str) and x for x in f)):
            errs.append(f"_nouns has no [singular, plural] for {w!r} (plural() at app.js:{lines[0]})")
    # 5. templates with ${} as keys, local t / tn / ta that hide the helpers, f-strings as Python keys
    for ln, txt in js["bad"]:
        if not area or fa.get(enclosing(table, ln)) == area:
            errs.append(f"app.js:{ln}: a template with ${{...}} as a key ({txt[:60]!r}) - use {{placeholders}} + vars")
    for x in js["shadow"]:
        if not area or fa.get(x["fn"]) == area:
            errs.append(f"app.js:{x['line']} {x['fn']}: a local {x['name']!r} hides {x['name']}() - rename it")
    for rel, r in G["py"].items():
        for ln, txt in r["bad"]:
            errs.append(f"{rel}:{ln}: an f-string as a key ({txt[:60]!r}) - use {{placeholders}} + vars")
    # 6. es.json follows the parts
    merged, clashes = merge_parts(lang, [])
    errs += [f"clash: {c}" for c in clashes]
    base = I18N_DIR / f"{lang}.json"
    if base.exists() and not area:
        cur = load_json(base, [])
        if cur != merged:
            warns.append(f"{base.relative_to(LAB)} is behind its parts - run: i18n_check.py merge (the app already "
                         f"reads the parts)")
    n_keys = len([k for k in cat if not k.startswith("_")])
    print(f"i18n check{' --area ' + area if area else ''} ({lang}): {n_keys} translations, {len(nouns)} nouns, "
          f"{len(used)} keys in the code, {len(js['dynamic'])} t() calls with a key from data")
    if area:
        items = todo_items(G, area) if area_group(amap, area) else []
        extra = collections.Counter(m["kind"] for m in items if m["kind"] in ("label", "number"))
        print(f"  {area}: {len(items) - sum(extra.values())} texts not wrapped yet"
              + (f" (+ {extra['label']} label sites, {extra['number']} numbers)" if extra else "") + f" (todo {area})")
    for w in warns:
        print("  warning:", w)
    for e in errs:
        print("  ERROR:", e)
    print("FAIL" if errs else "PASS", f"- {len(errs)} errors, {len(warns)} warnings")
    return 1 if errs else 0


def cmd_scan(show: bool, lang: str) -> int:
    G = gather(lang)
    cat = G["cat"]
    js, ix = G["js"], G["index"]
    py_open = [m for r in G["py"].values() for m in r["msgs"] if not (m["kind"] == "table" and m["text"] in cat)]
    mo_open = [m for m in G["motion"] if m["text"] not in cat]
    print(f"app.js: {len(js['msgs'])} texts not wrapped ({len({m['text'] for m in js['msgs']})} distinct), "
          f"{len(js['keys'])} keys wrapped, {len(js['labels'])} label sites, {len(js['numbers'])} numbers with "
          f"toFixed, {len(js['dynamic'])} t() from data")
    print(f"index.html: {len(ix['msgs'])} not wrapped, {len(ix['keys'])} wrapped")
    by = collections.Counter(m["kind"] for m in py_open)
    print(f"server (Python, {len(G['py'])} files): {len(py_open)} not wrapped - " +
          ", ".join(f"{k} {v}" for k, v in by.most_common()) +
          f"; {sum(len(r['keys']) for r in G['py'].values())} keys wrapped")
    print(f"report.html: {len(G['report']['msgs'])} texts")
    print(f"Motion Graphics library: {len(mo_open)} of {len(G['motion'])} labels without a translation "
          f"({len({m['text'] for m in mo_open})} distinct)")
    print(f"catalogue {lang}: {len([k for k in cat if not k.startswith('_')])} translations, "
          f"{len(cat.get('_nouns') or {})} nouns; waiting for the other window: {', '.join(WAITS)}")
    if show:
        for m in js["msgs"] + ix["msgs"] + py_open + G["report"]["msgs"] + mo_open:
            print(f"{m['file']}:{m['line']}  [{m['fn']}] {m['kind']}: {m['text'][:140]}")
    return 0


def cmd_todo(area: str, as_json: bool, lang: str) -> int:
    G = gather(lang)
    items = todo_items(G, area)
    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=1))
        return 0
    for m in items:
        print(f"{m['file']}:{m['line']}  [{m['fn']}] {m['kind']}: {m['text'][:160]}")
    js = area_group(area_map(), area) == "app.js"          # app.js: label sites + numbers apart from its texts
    labels = sum(1 for m in items if js and m["kind"] == "label")
    nums = sum(1 for m in items if js and m["kind"] == "number")
    print(f"-- {area}: {len(items) - labels - nums} texts not wrapped yet" + (f" + {labels} label sites" if labels else "")
          + (f" + {nums} numbers (dec)" if nums else ""))
    return 0


def partition(weights: list[int], k: int) -> list[int]:
    """Cut a list into k contiguous runs of about the same sum: the cuts with the smallest sum of squared distances of
    the runs' sums from their mean (dynamic programming over the items that weigh something; an item that weighs
    nothing goes with the run after it - a page's tables and helpers stand before the page) -> each run's start."""
    idx = [i for i, w in enumerate(weights) if w > 0]
    k = max(1, min(k, len(idx)))
    if k == 1:
        return [0]
    pre = [0]
    for i in idx:
        pre.append(pre[-1] + weights[i])
    n, mean, inf = len(idx), pre[-1] / k, float("inf")
    best = [[inf] * (n + 1) for _ in range(k + 1)]
    back = [[0] * (n + 1) for _ in range(k + 1)]
    best[0][0] = 0.0
    for r in range(1, k + 1):
        prev, row, brow = best[r - 1], best[r], back[r]
        for j in range(r, n - (k - r) + 1):
            b, bi, pj = inf, 0, pre[j]
            for i in range(r - 1, j):
                if prev[i] < b:
                    d = pj - pre[i] - mean
                    v = prev[i] + d * d
                    if v < b:
                        b, bi = v, i
            row[j], brow[j] = b, bi
    cuts, j = [], n
    for r in range(k, 0, -1):
        j = back[r][j]
        cuts.append(j)
    return [0] + [idx[c - 1] + 1 for c in reversed(cuts[:-1])]


# an area's name = the part of the app most of its texts belong to (by function name; else its section of app.js)
FN_WORD = [
    ("home", r"pageHome|heroAnim|HERO_LINES|WAYS|wayActs|roadmap\w*|sideUpdate|checkUpdates|update\w*|newsModal|"
             r"whatsNew\w*|testingText|knowledgeText"),
    ("analyser", r"pageRefs?|refCard|pageThumbs|setCard|pageTexts|tx\w+|addTexts\w*|addVideos\w*|addThumbs\w*|"
                 r"moreThumbs\w*|overviewTab|contentTab|colour\w*|wireColour|flow\w*|feedbackModal|sendFeedback|"
                 r"waiting\w*|wait[A-Z]\w*|FOCUS\w*|focusChip|estWords|TS_\w+|ts[A-Z]\w*|BD|uploadThumb"),
    ("editor", r"pageProjects?|proj\w+|createVideoModal|NE_\w+|bulkEditModal|batchRows|render[A-Z]\w*|drawIndex|"
               r"outcome\w*|wireOutcome|packaging\w*|wirePackaging|ck[A-Z]\w*|CHECK_\w+|font[A-Z]\w*|FONT_\w+|"
               r"gset\w*|livePreview|look\w*|gthumb|captions\w*|tookPanel|liveLine|reviewSummary|madeFrom\w*|"
               r"renameModal|genChip|reviewChip|RATE|pname"),
    ("memory", r"pageMemory|mem[A-Z]\w*|MEM_\w+|cardModal|RKIND|sharedChip|shDay|fmtNum|REVIEW_INCOMING"),
    ("prompts", r"pagePrompts|prompt[A-Z]\w*|PFILTERS|PSTEPS|PSTEP_\w+|VSTAGE|pstate|pcheck\w*|pstyle\w*|pneeds|"
                r"ptool\w*|psource|pused\w*|pstars|KSHORT|SLOT_LABEL|BRIEF_GROUPS|RUN|PURPOSES|PSRC|styleModal|"
                r"remixModal|forModal|kindModal|renamePromptModal|delPromptModal|addPromptsModal|newPromptForm|"
                r"havePromptForm|aiPromptsModal|isTalk|optCmd|chkCmd"),
    ("prepare", r"pagePrepare|script[A-Z]\w*|title[A-Z]\w*|filmItModal|teleprompter|talk[A-Z]\w*|SP_\w+|sp[A-Z]\w*|"
                r"ROAD|useTitleModal|uploadClip|folderName|tchars|fmtSecs"),
    ("motion", r"pageMotion|motion[A-Z]\w*|logo[A-Z]\w*|LOGO_\w+|MKIND|MSTATUS\w*"),
    ("generator", r"pageGenerate|generateModal|gen[A-Z]\w*"),
    ("settings", r"pageSettings|pageJobs|pageStorage|pageSkills|setTabs|upstreamBox|downloadModal|langRow|metaModal"),
]
SECTION_WORD = {"home": "home", "the workflow of a reference": "analyser", "delete (Recycle Bin)": "analyser",
                "videos (analyses)": "analyser", "projects": "editor", "Claude's memory": "memory",
                "prompts (0.4)": "prompts", "prepare": "prepare", "Motion Graphics (0.5.0)": "motion",
                "skills": "settings", "jobs": "settings", "storage": "settings", "downloads (yt-dlp)": "settings",
                "settings": "settings", "category / tags editor": "settings"}       # the rest: "shell"
# the Python files in 3 areas by what their words are about (a new file: the smallest area)
PY_AREAS = {"server-app": ["tools/motionlab/app/server.py", "tools/motionlab/app/data.py", "tools/motionlab/app/system.py",
                           "tools/motionlab/app/jobs.py", "tools/motionlab/app/jobtools.py",
                           "tools/motionlab/app/updater.py", "tools/motionlab/app/report.py",
                           "tools/motionlab/app/trash.py", "tools/motionlab/app/player.py", "tools/download.py"],
            "server-scripts": ["tools/motionlab/script.py", "tools/motionlab/prompts.py", "tools/motionlab/publish.py",
                               "tools/motionlab/thumbnail.py", "tools/motionlab/textsets.py"],
            "server-labels": ["tools/motionlab/knowledge.py", "tools/motionlab/style.py", "tools/motionlab/thumbsets.py",
                              "tools/motionlab/taxonomy.py", "tools/motionlab/styles.py", "tools/motionlab/logos.py",
                              "tools/motionlab/fonts.py", "tools/motionlab/colour.py", "tools/motionlab/profile.py",
                              "tools/motionlab/usage.py", "tools/motionlab/speech.py", "tools/motionlab/upstream.py"]}


def cmd_areas(lang: str) -> int:
    G = gather(lang)
    js = G["js"]
    cnt = collections.Counter(m["fn"] for m in js["msgs"])
    fns = [fn for _, fn in js["decls"]]
    lines = {fn: ln for ln, fn in js["decls"]}
    w = [cnt.get(fn, 0) for fn in fns]
    starts = partition(w, N_JS_AREAS)
    secs = js["sections"]

    def word(fn):
        for wd, rx in FN_WORD:
            if re.fullmatch(rx, fn):
                return wd
        k = bisect.bisect_right([a for a, _ in secs], lines[fn]) - 1
        return SECTION_WORD.get(secs[k][1] if k >= 0 else "", "shell")

    runs = [fns[a:b] for a, b in zip(starts, starts[1:] + [len(fns)])]
    base = []
    for r in runs:
        by = collections.Counter()
        for f in r:
            by[word(f)] += cnt.get(f, 0)
        top = [x for x, _ in by.most_common(2)] or [word(r[0])]
        tot = sum(by.values()) or 1
        base.append(f"{top[0]}-{top[1]}" if len(top) > 1 and by[top[1]] >= 0.3 * tot else top[0])
    named, seen, totals = {}, collections.Counter(), collections.Counter(base)
    for b, r in zip(base, runs):
        seen[b] += 1
        named[f"{b}-{seen[b]}" if totals[b] > 1 else b] = r
    print(f"{'function':32} {'line':>6} {'texts':>6}  area")
    for name, r in named.items():
        for fn in r:
            if cnt.get(fn):
                print(f"{fn:32} {lines[fn]:6d} {cnt[fn]:6d}  {name}")
    print("\napp.js areas:")
    counts = {}
    for name, r in named.items():
        counts[name] = sum(cnt.get(f, 0) for f in r)
        print(f"  {name:24} {counts[name]:5d} texts  {len(r):4d} functions  lines {lines[r[0]]}-{lines[r[-1]]}")
    # the Python files with words for the user: 3 areas (whole files)
    cat = G["cat"]
    pyc = {rel: sum(1 for m in r["msgs"] if not (m["kind"] == "table" and m["text"] in cat)) for rel, r in G["py"].items()}
    bins = {b: [f for f in fs if f in pyc] for b, fs in PY_AREAS.items()}
    tot = {b: sum(pyc[f] for f in fs) for b, fs in bins.items()}
    for rel in pyc:
        if not any(rel in fs for fs in bins.values()):
            b = min(tot, key=tot.get)
            bins[b].append(rel); tot[b] += pyc[rel]
    print("\nPython areas:")
    for b, fs in bins.items():
        counts[b] = tot[b]
        print(f"  {b:24} {tot[b]:5d} texts  {', '.join(Path(f).name for f in fs)}")
    counts["index"] = len(G["index"]["msgs"])
    counts["report"] = len(G["report"]["msgs"])
    counts["motion-library"] = len([m for m in G["motion"] if m["text"] not in cat])
    print(f"\nindex: {counts['index']}  report: {counts['report']}  motion-library: {counts['motion-library']} "
          f"({len({m['text'] for m in G['motion']})} distinct)")
    out = {"_about": "The translating areas (tools\\dev\\i18n_check.py areas, 2026-10-19). Each area writes ONLY "
                     "tools\\motionlab\\app\\ui\\i18n\\parts\\es.<area>.json and wraps the texts of its own functions / "
                     "files (todo <area>); a function added later belongs to the area of the function above it. "
                     "'core' (es.core.json) = the mechanism's words, _nouns and _meta (the glossary).",
           "app.js": named, "python": {b: fs for b, fs in bins.items()},
           "index.html": {"index": ["tools/motionlab/app/ui/index.html"]},
           "report_html.py": {"report": ["tools/motionlab/report_html.py"]},
           "motion": {"motion-library": ["tools/overlays/motion/*/template.json (name, what)",
                                         "tools/overlays/motion/*/index.html (setting and option labels)"]},
           "_counts": counts, "_waits": WAITS}
    AREAS_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"-> {AREAS_FILE.relative_to(LAB)}")
    return 0


def dump_catalogue(cat: dict) -> str:
    """The catalogue as JSON with one entry a line (a count's forms and a noun's two forms on that line too), so a
    3,000-entry file reads and diffs line by line; _meta as indented JSON."""
    one = lambda v: json.dumps(v, ensure_ascii=False)                    # noqa: E731
    out = []
    for k, v in cat.items():
        if k == "_meta":
            out.append(f" {one(k)}: " + json.dumps(v, ensure_ascii=False, indent=1).replace("\n", "\n "))
        elif k == "_nouns" and isinstance(v, dict):
            out.append(f" {one(k)}: {{\n" + ",\n".join(f"  {one(a)}: {one(b)}" for a, b in v.items()) + "\n }")
        else:
            out.append(f" {one(k)}: {one(v)}")
    return "{\n" + ",\n".join(out) + "\n}\n"


def cmd_merge(lang: str) -> int:
    errors: list = []
    merged, clashes = merge_parts(lang, errors)
    for e in errors + clashes:
        print("  ERROR:", e)
    if errors or clashes:
        print("FAIL - nothing written: fix the parts first")
        return 1
    p = I18N_DIR / f"{lang}.json"
    text = dump_catalogue(merged)
    assert json.loads(text) == merged
    p.write_text(text, encoding="utf-8")
    print(f"{p.relative_to(LAB)}: {len([k for k in merged if not k.startswith('_')])} translations, "
          f"{len(merged.get('_nouns') or {})} nouns from {len(part_files(lang))} parts")
    return 0


def cmd_selfcheck() -> int:
    js = ("const A = t('Saved {n}', {n: 3});\nfunction f(x) {\n  const n = (v, w) => plural(v, w);\n"
          "  return `<div title=\"Close it\">Hello there</div><span>${t('Open|verb')}</span>"
          "<span>${tn(x.length, '{n} video', '{n} videos')}</span> ${plural(2, 'clip')} ${n(3, 'cut')}"
          " ${x ? 'some words here' : ta('Shown words')}`;\n}\n"
          "function g(t) { return t('Oops') + `${dyn}` + t(x.label) + esc(o.label); }\n"
          "const FAM = {'Hard cut': '#fff'};\n// t('in a comment')\nconst s = `don't(x)`;\n"
          "const h = x => `<i style=\"left:${(x * 2).toFixed(1)}%\">${x.toFixed(2)} s</i>`;\n")
    r = js_report(js)
    assert [(n["fn"], "x.toFixed(2)" in n["text"]) for n in r["numbers"]] == [("h", True)], r["numbers"]
    assert set(r["keys"]) == {"Saved {n}", "Open|verb", "{n} videos", "Shown words", "Oops"}, r["keys"]
    assert r["ones"] == {"{n} videos": "{n} video"}, r["ones"]
    texts = {m["text"] for m in r["msgs"]}
    assert {"Hello there", "Close it", "some words here"} <= texts and "Hard cut" not in texts, texts
    assert not any("Saved" in x or "Shown" in x for x in texts), texts
    assert set(r["nouns"]) == {"clip", "cut"}, r["nouns"]
    assert [x["name"] for x in r["shadow"]] == ["t"] and r["shadow"][0]["fn"] == "g", r["shadow"]
    assert len(r["dynamic"]) == 1 and r["labels"] and r["labels"][0]["text"] == "esc(o.label)", (r["dynamic"], r["labels"])
    py = ("from motionlab import i18n as I18N\n\ndef f(n):\n    if n < 0:\n        raise ValueError(I18N.t('no such {x}', x=n))\n"
          "    if n > 9:\n        raise ValueError('too many things here')\n    return I18N.tn(n, '{n} file', '{n} files')\n")
    p = py_report("x.py", py)
    assert set(p["keys"]) == {"no such {x}", "{n} files"} and p["ones"] == {"{n} files": "{n} file"}, p
    assert [m["text"] for m in p["msgs"]] == ["too many things here"], p["msgs"]
    e, _ = entry_problems("Hi <b>{name}</b>", "Hola {name}", set())
    assert len(e) == 1 and "tags" in e[0], e
    e, _ = entry_problems("{n} videos", {"one": "un vídeo", "other": "{n} vídeos"}, set())
    assert not e, e
    e, w = entry_problems("Two words", "Two words", set())
    assert not e and w, w
    assert partition([5, 1, 1, 5, 1, 1, 5], 3) == [0, 3, 6] or len(partition([5, 1, 1, 5, 1, 1, 5], 3)) == 3
    assert js_cook(r"aé\n\'b") == "aé\n'b"
    print("i18n_check selfcheck: OK")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--area")
    c.add_argument("--lang", default="es")
    s = sub.add_parser("scan")
    s.add_argument("--list", action="store_true")
    s.add_argument("--lang", default="es")
    t = sub.add_parser("todo")
    t.add_argument("area")
    t.add_argument("--json", action="store_true")
    t.add_argument("--lang", default="es")
    a = sub.add_parser("areas")
    a.add_argument("--lang", default="es")
    m = sub.add_parser("merge")
    m.add_argument("--lang", default="es")
    sub.add_parser("selfcheck")
    o = ap.parse_args()
    if o.cmd == "check":
        return cmd_check(o.area, o.lang)
    if o.cmd == "scan":
        return cmd_scan(o.list, o.lang)
    if o.cmd == "todo":
        return cmd_todo(o.area, o.json, o.lang)
    if o.cmd == "areas":
        return cmd_areas(o.lang)
    if o.cmd == "merge":
        return cmd_merge(o.lang)
    return cmd_selfcheck()


if __name__ == "__main__":
    sys.exit(main())
