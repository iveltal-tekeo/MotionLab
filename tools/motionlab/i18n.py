"""The app's words in the user's language (2026-10-18, the user: "we need a spanish version of the entire app" - Spain,
tú; "Claude's stored knowledge stays English": only the app's words and Claude's chat follow the language).

ONE catalogue per language, read by the page (server._index inlines it) and by the server (this module):
tools\\motionlab\\app\\ui\\i18n\\<lang>.json = one flat object. Key = the English text exactly as the code writes it,
with {named} placeholders and inline tags kept; value = the translation, or {"one": ..., "other": ...} for a count
(the key = the English "other" form). "Open|verb" = a key with a context (shown without it in English). "_nouns" =
plural()'s nouns {"video": ["vídeo", "vídeos"]}, "_meta" = the language + the glossary, "_by_key" = keys the page
looks up from data the check cannot see (tools\\dev\\i18n_check.py does not call them unused). The part files
ui\\i18n\\parts\\<lang>.<area>.json (one per translating area, the same shape; the source of the words) are read
too, laid over the catalogue, so work that `tools\\dev\\i18n_check.py merge` has not folded into <lang>.json yet
already shows. English needs no file: a key that is missing shows its English. settings.json and the catalogue files
are looked at again at most once a second (RECHECK_S; system.save calls forget()), so t() costs a few dict lookups.

    lang()                      "en" | "es": MOTIONLAB_LANG when it is set (jobs.py starts every tool with the app's),
                                else - in the app's own server (follow_settings()) - Settings > Language
                                (settings.json "language", read again when the file changes), else "en": the
                                self-test and the CLI tools Claude runs stay English unless MOTIONLAB_LANG says so
    t(en, **vars)               the text in lang(); {name} filled from vars (only when vars are given)
    tn(n, one, other, **vars)   a count: the language's plural form; {n} = the number
    page_script(lang)           index.html's <script>window.ML_I18N = {...}</script> (English: {})
    fill_html(page, lang)       index.html's {{t:English text}} -> the translation (HTML-escaped; plain text only,
                                no tags inside; the key = the text with its entities read: What&#39;s new = What's new)

Use t() / tn() where words are BUILT on the server (raise messages that reach a toast, job titles, check sentences,
delete warnings, live-line words). Fixed labels sent as data (CATEGORIES, PRESETS, KINDS, ...) are translated on the
page by key. Never translated: Claude commands, ids, file names, the f480 (00:00:16:00) notation, the MOTIONLAB
FEEDBACK export, console output and job logs (app CLAUDE.md "Languages")."""
from __future__ import annotations

import html
import json
import os
import re
import threading
import time
from pathlib import Path

from .util import LAB

LANGUAGES = ("en", "es")                       # Settings > Language (system.save refuses any other)
NAMES = {"en": "English", "es": "Español"}     # each language in its own words (the Settings row)
DIR = Path(__file__).resolve().parent / "app" / "ui" / "i18n"
SETTINGS = LAB / "settings.json"
CONTEXT = re.compile(r"(?<=\S)\|[a-z][a-z0-9 _-]{0,40}$")       # "Open|verb": the context after the last |
VAR = re.compile(r"\{(\w+)\}")
PAGE_SKIP = ("_meta", "_by_key")               # the page needs the words and _nouns only
RECHECK_S = 1.0                                # settings.json and the catalogues: looked at again at most once a second
_LOCK = threading.Lock()
_follow = False
_settings: tuple = (None, "en", -RECHECK_S)    # (the file's stat key, its language, when checked)
_cats: dict = {}                               # lang -> (stat key of its files, catalogue, page json, when checked)


def follow_settings(on: bool = True) -> None:
    """The app's server: lang() follows Settings > Language (server.make calls it once)."""
    global _follow
    _follow = bool(on)


def forget() -> None:
    """settings.json was just written (system.save): the next lang() reads it again, so the page that reloads right
    after Settings > Language comes in the new language."""
    global _settings
    _settings = (_settings[0], _settings[1], -RECHECK_S)


def _norm(v) -> str:
    v = str(v or "").strip().lower()
    return v if v in LANGUAGES else "en"


def settings_lang() -> str:
    """settings.json "language" (read again when the file changed, looked at at most once a second); "en" when unset
    or unknown."""
    global _settings
    now = time.monotonic()
    if now - _settings[2] < RECHECK_S:
        return _settings[1]
    try:
        st = SETTINGS.stat()
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        _settings = (None, "en", now)
        return "en"
    if _settings[0] != key:
        try:
            v = json.loads(SETTINGS.read_text(encoding="utf-8")).get("language")
        except (OSError, ValueError, AttributeError):
            v = None
        _settings = (key, _norm(v), now)
    else:
        _settings = (key, _settings[1], now)
    return _settings[1]


def lang() -> str:
    env = os.environ.get("MOTIONLAB_LANG", "").strip()
    if env:
        return _norm(env)
    return settings_lang() if _follow else "en"


def files(lg: str) -> list[Path]:
    """The catalogue of a language, then its part files (not merged yet) - the order they are laid over each other."""
    return [DIR / f"{lg}.json"] + sorted((DIR / "parts").glob(f"{lg}.*.json"))


def merge_into(cat: dict, part: dict) -> list[str]:
    """Lay one part over a catalogue (in place): words replace words, _nouns / _meta merge, _by_key adds up. Returns
    the keys whose translation changed (a conflict when both were set)."""
    clash = []
    for k, v in part.items():
        if k in ("_nouns", "_meta") and isinstance(v, dict):
            have = cat.setdefault(k, {})
            for nk, nv in v.items():
                if nk in have and have[nk] != nv and not isinstance(nv, dict):
                    clash.append(f"{k}.{nk}")
                if isinstance(nv, dict) and isinstance(have.get(nk), dict):
                    have[nk] = {**have[nk], **nv}
                else:
                    have[nk] = nv
        elif k == "_by_key" and isinstance(v, list):
            cat[k] = sorted(set(cat.get(k) or []) | {str(x) for x in v})
        else:
            if k in cat and cat[k] != v:
                clash.append(k)
            cat[k] = v
    return clash


def _load(lg: str) -> tuple[dict, str]:
    if lg == "en":
        return {}, "{}"
    got, now = _cats.get(lg), time.monotonic()
    if got and now - got[3] < RECHECK_S:           # a server word built many times per request: no file look-ups
        return got[1], got[2]
    fs, key = [], []
    for p in files(lg):
        try:
            st = p.stat()
        except OSError:
            continue
        fs.append(p)
        key.append((p.name, st.st_mtime_ns, st.st_size))
    key = tuple(key)
    if got and got[0] == key:
        _cats[lg] = (key, got[1], got[2], now)
        return got[1], got[2]
    with _LOCK:
        cat: dict = {}
        for p in fs:
            try:
                part = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue                           # a broken part file never breaks the app (i18n_check.py says why)
            if isinstance(part, dict):
                merge_into(cat, part)
        page = json.dumps({k: v for k, v in cat.items() if k not in PAGE_SKIP}, ensure_ascii=False,
                          separators=(",", ":")).replace("<", "\\u003c")      # safe inside <script>
        _cats[lg] = (key, cat, page, now)
    return cat, page


def catalogue(lg: str | None = None) -> dict:
    return _load(_norm(lg or lang()))[0]


def page_script(lg: str) -> str:
    """The catalogue for the page, inlined before app.js (so its label tables are translated as they load)."""
    return f"<script>window.ML_I18N = {_load(_norm(lg))[1]};</script>"


def english(key: str) -> str:
    """A key as English shows it: without its |context."""
    return CONTEXT.sub("", str(key))


def fill(s: str, vars: dict) -> str:
    return VAR.sub(lambda m: str(vars[m[1]]) if m[1] in vars else m[0], s) if vars else s


def num(v, lg: str | None = None) -> str:
    """A number as the language writes it: English as Python prints it; Spanish 4,5 and 12.345 (from 10 000 up,
    like Intl.NumberFormat("es"))."""
    if (lg or lang()) == "en" or isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if "e" in s or "inf" in s or "nan" in s:
        return s
    whole, _, frac = s.partition(".")
    sign = "-" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    if len(whole) > 4:
        whole = f"{int(whole):,}".replace(",", ".")
    return sign + whole + ("," + frac if frac else "")


def _form(lg: str, n) -> str:
    """CLDR's plural category for English and Spanish: one / many (Spanish millions: "1 millón de vídeos") / other."""
    try:
        x = float(n)
    except (TypeError, ValueError):
        return "other"
    if x == 1:
        return "one"
    if lg == "es" and x and x == int(x) and int(x) % 1_000_000 == 0:
        return "many"
    return "other"


def text(cat: dict, en: str, vars: dict | None = None) -> str:
    """t() on a given catalogue (the selfcheck uses it with its own)."""
    v = cat.get(en)
    if isinstance(v, dict):
        v = v.get("other")
    return fill(v if isinstance(v, str) and v else english(en), vars or {})


def count(cat: dict, lg: str, n, one: str, other: str, vars: dict | None = None) -> str:
    """tn() on a given catalogue."""
    vv = {"n": num(n, lg), **(vars or {})}
    v = cat.get(other)
    if isinstance(v, dict):
        s = v.get(_form(lg, n)) or v.get("other") or v.get("one")
        if isinstance(s, str) and s:
            return fill(s, vv)
    elif isinstance(v, str) and v:
        return fill(v, vv)
    return fill(english(one if _form("en", n) == "one" else other), vv)


def t(en: str, **vars) -> str:
    lg = lang()
    return text(catalogue(lg), en, vars) if lg != "en" else fill(english(en), vars)


def tn(n, one: str, other: str, **vars) -> str:
    lg = lang()
    return count(catalogue(lg), lg, n, one, other, vars)


_HTML_T = re.compile(r"\{\{t:(.+?)\}\}", re.S)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fill_html(page: str, lg: str) -> str:
    """index.html's {{t:English}} texts (a text node or an attribute value) in the language - the English itself
    when there is no translation (so the English page stays byte for byte what it was). The key is the text as the
    page shows it (entities read), the same key app.js would use."""
    cat = catalogue(lg) if _norm(lg) != "en" else {}

    def one(m):
        key = html.unescape(m[1])
        return _esc(text(cat, key)) if key in cat else m[1]
    return _HTML_T.sub(one, page)


def selfcheck() -> None:
    """Fast: the fallbacks, placeholders, plural forms, contexts, numbers, the page script and the real catalogue."""
    cat = {"{n} videos": {"one": "{n} vídeo", "other": "{n} vídeos"}, "Open|verb": "Abrir", "Hi {name}": "Hola {name}",
           "Saved": "Guardado", "_nouns": {"video": ["vídeo", "vídeos"]}}
    assert text(cat, "Hi {name}", {"name": "Ana"}) == "Hola Ana"
    assert text(cat, "Not there {x}", {"x": 1}) == "Not there 1"          # missing = English, filled
    assert text(cat, "Open|verb") == "Abrir" and text({}, "Open|verb") == "Open" and english("a | b") == "a | b"
    assert text({}, "Keep {braces} as they are") == "Keep {braces} as they are"
    assert count(cat, "es", 1, "{n} video", "{n} videos") == "1 vídeo"
    assert count(cat, "es", 0, "{n} video", "{n} videos") == "0 vídeos"
    assert count(cat, "es", 12345, "{n} video", "{n} videos") == "12.345 vídeos"
    assert count(cat, "es", 2_000_000, "{n} video", "{n} videos") == "2.000.000 vídeos"     # "many" -> other
    assert count({}, "en", 1, "{n} video", "{n} videos") == "1 video"
    assert count({}, "en", 3, "{n} video", "{n} videos") == "3 videos"
    assert num(4.5, "es") == "4,5" and num(1234, "es") == "1234" and num(-12345.5, "es") == "-12.345,5"
    assert num(4.5, "en") == "4.5" and num("x", "es") == "x"
    assert _form("es", 1) == "one" and _form("es", 1_000_000) == "many" and _form("es", 2) == "other"
    assert fill_html('<b title="{{t:Close (Esc)}}">{{t:Home}}</b>', "en") == '<b title="Close (Esc)">Home</b>'
    assert fill_html('<b title="{{t:What&#39;s new}}">{{t:Tom &amp; Jerry}}</b>', "en") == \
        '<b title="What&#39;s new">Tom &amp; Jerry</b>'
    m = _HTML_T.search("{{t:What&#39;s new}}")
    assert html.unescape(m[1]) == "What's new" and _esc(text({"What's new": 'Lo "nuevo"'}, "What's new")) == \
        "Lo &quot;nuevo&quot;"
    old = os.environ.pop("MOTIONLAB_LANG", None)
    try:
        assert lang() in LANGUAGES
        os.environ["MOTIONLAB_LANG"] = "es"
        assert lang() == "es"
        os.environ["MOTIONLAB_LANG"] = "xx"
        assert lang() == "en"
    finally:
        os.environ.pop("MOTIONLAB_LANG", None)
        if old is not None:
            os.environ["MOTIONLAB_LANG"] = old
    assert page_script("en") == "<script>window.ML_I18N = {};</script>"
    es, page = _load("es")
    assert isinstance(es, dict) and "<" not in page and json.loads(page).get("_meta") is None
    assert page_script("es") == f"<script>window.ML_I18N = {page};</script>"
    print(f"i18n selfcheck: OK ({len([k for k in es if not k.startswith('_')])} Spanish texts, "
          f"{len(es.get('_nouns', {}))} nouns)")
