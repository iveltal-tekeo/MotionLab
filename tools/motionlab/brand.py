"""My Brand (0.6.0, Content agency): what Claude knows about the user's brand - one file on this PC,
`knowledge\\local\\brand.json`, never shared unless the user shares it. The app's My Brand page reads and writes it
(GET / POST /api/brand); the skills read it (0.6.0 step 4); New edit offers its colours as the first palette (step 3);
Claude fills it from the user's website (step 2) - the user ticks what is right.

brand.json:
  "name":      "RIFT", "about": "what the brand does, in a line"
  "goal":      {"picks": [ids of GOALS], "words": "the user's own words"}
  "audience":  ["who the videos are for", ...]                       (<= 12, each <= 80 characters)
  "identity":  {"colours": [{"hex": "#2eaa5c", "name": "Kutxiletto green"}] (<= 6), "voice": "close and direct",
                "logo": "knowledge/local/brand/logo.png" | "",          (the logo: save_logo, a picture the user picks)
                "sound_logo": "knowledge/local/brand/sound_logo.wav" | "",  (a short sound: save_sound_logo, made with
                                                                    ElevenLabs or a file the user picks)
                "fonts": {"heading": "Space Grotesk", "body": "Inter"},  (families of the lab's font library)
                "captions": {"look": "clean_box", "font", "case": upper|sentence, "color", "highlight",
                             "motion": highlight|pop|line, "position": bottom|middle|top, "box": true|false|null}}
                (the caption style - "" / null = the look's own; `overlay.py captions ... --brand` applies it)
  "site":      {"url": "https://...", "read": "2026-10-25 21:10" | null,   (read = the last Import from your website)
                "text": "knowledge/local/brand/site_text.md" | ""}       (what the website says, if the user kept it)
  "pillars":   [{"name": "Behind the scenes", "what": "...", "series": "Day N on set"}]   (<= 6, what they post about)
  identity "tone": {"dims": {casual|funny|cheeky|excited: 0..4 | null}, "use": [...], "avoid": [...], "lines": [...]}
               (the voice in their own words); a product also has "promo" (a code) and "sponsored" (a paid partnership)
  "pages":     [{"platform": "youtube", "url": "https://www.youtube.com/@x", "cta": "subscribe for ..."}] (one each)
  "look":      {"like": ["<analysis folder>", ...]}   (<= 3 analysed videos = the brand's pacing, transitions, grade)
  "glossary":  [{"word": "RIFT", "say": "rift"}]       (<= 60: names spelled exactly, never translated; say = how it is
               said, optional - captions' speech to text gets them as names)
  "catalogue": [{"id": "p1", "name", "what", "price", "url", "image", "use": true}]  (<= 200; use = Claude may put
               it in videos; image = knowledge/local/brand/products/p1.png, from the import)
  "updated":   "2026-10-25 21:10"
Every save is checked (`clean`): unknown keys dropped, text trimmed and cut to its length, colours #rrggbb, the site a
web address, a page an address of its platform; a product without a name is dropped.
Import from your website (step 2, `motionlab\\siteread.py`): found.json in knowledge\\local\\brand\\import\\ ->
the page's tick list -> take_import(picks) copies the ticked ones in.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from . import i18n as I18N
from .util import LAB

PATH = LAB / "knowledge" / "local" / "brand.json"
GOALS = ("sell", "personal_brand", "community", "inform")      # the mock-up's four (slide 10)
MAX = {"words": 400, "aud": 80, "aud_n": 12, "colour_name": 40, "colours": 6, "voice": 300, "url": 300,
       "name": 80, "what": 160, "price": 24, "products": 200, "about": 300, "cta": 120, "word": 40, "say": 60,
       "words_n": 60}


LOGO_DIR = PATH.parent / "brand"
LOGO_EXT = (".png", ".jpg", ".jpeg", ".webp", ".svg")
PRODUCT_DIR = LOGO_DIR / "products"
PRODUCT_MEDIA_N, PRODUCT_VIDEO_MB = 6, 30        # 5b: a product's screenshots / screen recordings (the page sends base64)
SITE_TEXT = LOGO_DIR / "site_text.md"                   # what the website says (Import from your website, ticked)
PLATFORMS = {"youtube": "YouTube", "tiktok": "TikTok", "instagram": "Instagram", "x": "X", "linkedin": "LinkedIn",
             "facebook": "Facebook", "threads": "Threads", "twitch": "Twitch"}     # the ids = siteread.SOCIAL's
# a colour's job (2026-10-25, with the import's screenshot palette): what it is for in a video
COLOUR_ROLES = ("background", "text", "accent", "neutral")
# logo versions (2026-10-26, step 3f): light = the one for dark backgrounds, dark = for light ones, icon = the mark
# alone (a corner, a small space) - knowledge\local\brand\logo_<kind>.<ext>; where = where videos put the logo
LOGO_KINDS = ("light", "dark", "icon")
LOGO_WHERE = ("end", "corner", "none")         # the end card (the default) | + small in a corner all along | nowhere
READ_TEXT, READ_BIG = 4.5, 3.0                 # contrast a text colour needs on its background (WCAG AA; big = titles)
LOGO_USE = {"light": "for dark backgrounds", "dark": "for light backgrounds", "icon": "the mark alone, for a corner"}
# the signature end card (2026-10-26, 5c): a Motion Graphics template filled from the brand - "end_card": {"style",
# "line" (the sign-off, <= 60)}; style "" = none picked (Claude's call)
END_STYLES = {"logo": "logo-reveal", "title": "title-card", "channel": "end-screen"}
END_LOGO_KEY = {"logo-reveal": "logo", "end-screen": "picture"}          # the setting that takes the logo picture
END_SOUNDS = ("", "logo")      # end_card "sound": "" = the template's own sound effects | "logo" = the sound logo
SOUND_EXT = (".wav", ".mp3", ".m4a", ".ogg", ".flac")
SOUND_LOGO_MAX_S = 8.0         # a sound logo is a few seconds - longer is a song, not a signature
LOGO_WHERE_DO = {"end": "the logo on the end card only", "corner": "the logo on the end card and small in a corner "
                 "the whole video (the icon if there is one; where it covers nothing)", "none": "no logo in the video"}
# the caption style (2026-10-25): a ready look of the captions graphic (its presets.json) + the brand's choices on top
CAPTION_LOOKS = ("classic", "clean_box", "keyword")     # (0.6.0 step 21: keyword = small words, one big one)
CAPTION = {"case": ("upper", "sentence"), "motion": ("highlight", "pop", "line"), "position": ("bottom", "middle", "top")}
CAPTION_Y = {"bottom": (78, 72), "middle": (50, 50), "top": (16, 20)}   # the graphic's y / y_upright (% from the top)
# 3c's rest (2026-10-26): words per line (0 = the look's own grouping, 6 at most) and the size against the look's own
CAPTION_WORDS = (1, 2, 3, 4, 6)
CAPTION_SIZE = {"s": 0.8, "m": 1.0, "l": 1.25, "xl": 1.5}
CAPTION_PRESETS = LAB / "tools" / "overlays" / "examples" / "captions" / "presets.json"


def _no_captions() -> dict:
    return {"look": "", "font": "", "case": "", "color": "", "highlight": "", "motion": "", "position": "", "box": None,
            "words": 0, "size": ""}


# the voice in the user's own words (2026-10-26, the research's 3b): four tone sliders (the NN/g dimensions, 0..4, 2 =
# the middle, None = not set), words to use / never to use, lines that sound like them
TONE_DIMS = {"casual": ("formal", "casual"), "funny": ("serious", "funny"), "cheeky": ("respectful", "cheeky"),
             "excited": ("calm", "excited")}


def _no_voice() -> dict:
    return {"dims": {k: None for k in TONE_DIMS}, "use": [], "avoid": [], "lines": []}


def empty() -> dict:
    return {"name": "", "about": "", "goal": {"picks": [], "words": ""}, "audience": [],
            "identity": {"colours": [], "voice": "", "logo": "", "logos": {k: "" for k in LOGO_KINDS}, "logo_where": "",
                         "sound_logo": "", "fonts": {"heading": "", "body": ""}, "captions": _no_captions(),
                         "tone": _no_voice()},
            "site": {"url": "", "read": None, "text": ""}, "pages": [], "pillars": [], "look": {"like": []}, "glossary": [],
            "end_card": {"style": "", "line": "", "sound": ""}, "catalogue": [], "updated": None}


def _s(v, n: int) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()[:n]


def _url(v) -> str:
    u = _s(v, MAX["url"])
    if not u:
        return ""
    if not re.match(r"https?://", u, re.I):
        u = "https://" + u
    if not re.fullmatch(r"https?://[\w.-]+\.[a-z]{2,}(?::\d+)?(?:/[^\s\"'<>]*)?", u, re.I):
        raise ValueError(I18N.t("not a web address: {url}", url=u))
    return u


def clean(body: dict) -> dict:
    """The page's data -> a valid brand.json (raises ValueError on a bad web address)."""
    b, out = body or {}, empty()
    g = b.get("goal") or {}
    out["goal"] = {"picks": [p for p in GOALS if p in (g.get("picks") or [])], "words": _s(g.get("words"), MAX["words"])}
    aud = [_s(a, MAX["aud"]) for a in (b.get("audience") or [])]
    out["audience"] = list(dict.fromkeys(a for a in aud if a))[:MAX["aud_n"]]
    idt = b.get("identity") or {}
    cols = []
    for c in idt.get("colours") or []:
        h = str((c or {}).get("hex") or "").strip().lower()
        if re.fullmatch(r"#[0-9a-f]{6}", h):
            cols.append({"hex": h, "name": _s(c.get("name"), MAX["colour_name"]),
                         "role": c.get("role") if c.get("role") in COLOUR_ROLES else ""})
    logo = str(idt.get("logo") or "").replace("\\", "/")              # only a logo save_logo wrote
    logo = logo if re.fullmatch(r"knowledge/local/brand/logo\.(png|jpe?g|webp|svg)", logo) and (LAB / logo).is_file() else ""
    lv = idt.get("logos") or {}
    logos = {k: (str(lv.get(k) or "").replace("\\", "/")) for k in LOGO_KINDS}
    logos = {k: (f if re.fullmatch(rf"knowledge/local/brand/logo_{k}\.(png|jpe?g|webp|svg)", f) and (LAB / f).is_file()
                 else "") for k, f in logos.items()}
    snd = str(idt.get("sound_logo") or "").replace("\\", "/")          # only one save_sound_logo wrote
    snd = snd if re.fullmatch(r"knowledge/local/brand/sound_logo\.(wav|mp3|m4a|ogg|flac)", snd) and (LAB / snd).is_file() else ""
    fams = {f["family"] for f in _font_families()}
    fo = idt.get("fonts") or {}
    cp = idt.get("captions") or {}
    hexes = {k: str(cp.get(k) or "").lower() for k in ("color", "highlight")}
    out["identity"] = {"colours": cols[:MAX["colours"]], "voice": _s(idt.get("voice"), MAX["voice"]), "logo": logo,
                       "logos": logos, "logo_where": idt.get("logo_where") if idt.get("logo_where") in LOGO_WHERE else "",
                       "sound_logo": snd,
                       "fonts": {k: (fo.get(k) if fo.get(k) in fams else "") for k in ("heading", "body")},
                       "captions": {"look": cp.get("look") if cp.get("look") in CAPTION_LOOKS else "",
                                    "font": cp.get("font") if cp.get("font") in fams else "",
                                    **{k: (cp.get(k) if cp.get(k) in v else "") for k, v in CAPTION.items()},
                                    **{k: (h if re.fullmatch(r"#[0-9a-f]{6}", h) else "") for k, h in hexes.items()},
                                    "box": cp.get("box") if isinstance(cp.get("box"), bool) else None,
                                    "words": int(cp["words"]) if str(cp.get("words")) in map(str, CAPTION_WORDS) else 0,
                                    "size": cp.get("size") if cp.get("size") in CAPTION_SIZE else ""},
                       "tone": _clean_tone(idt.get("tone") or {})}
    out["name"], out["about"] = _s(b.get("name"), MAX["name"]), _s(b.get("about"), MAX["about"])
    ec = b.get("end_card") or {}
    out["end_card"] = {"style": ec.get("style") if ec.get("style") in END_STYLES else "", "line": _s(ec.get("line"), 60),
                       "sound": ec.get("sound") if ec.get("sound") in END_SOUNDS else ""}
    pil, seen_p = [], set()                          # content pillars (2026-10-26): 3-6 themes, a series each (optional)
    for x in b.get("pillars") or []:
        n = _s((x or {}).get("name"), 60)
        if n and n.lower() not in seen_p and len(pil) < 6:
            seen_p.add(n.lower())
            pil.append({"name": n, "what": _s(x.get("what"), 160), "series": _s(x.get("series"), 80)})
    out["pillars"] = pil
    site = b.get("site") or {}
    txt = str(site.get("text") or "").replace("\\", "/")              # what the website says - only the file the import wrote
    out["site"] = {"url": _url(site.get("url")), "read": site.get("read") if isinstance(site.get("read"), str) else None,
                   "text": txt if txt == SITE_TEXT.relative_to(LAB).as_posix() and SITE_TEXT.is_file() else ""}
    from .siteread import SOCIAL
    pages = []
    for pg in b.get("pages") or []:
        plat, u = str((pg or {}).get("platform") or ""), _s((pg or {}).get("url"), MAX["url"])
        if plat not in PLATFORMS or plat in [x["platform"] for x in pages]:
            continue
        if u and not re.match(r"https?://", u, re.I):
            u = "https://" + u
        m = re.match(r"https?://" + SOCIAL[plat], u, re.I) if u else None
        if u and not m:
            raise ValueError(I18N.t("not a {platform} address: {url}", platform=PLATFORMS[plat], url=u))
        u = "https://" + m.group(0).split("://", 1)[1] if m else ""         # the profile itself (/videos ... cut)
        pages.append({"platform": plat, "url": u, "cta": _s(pg.get("cta"), MAX["cta"])})
    out["pages"] = pages
    from .util import ANALYSIS                       # your editing look: analyses on this PC only (a cheap check -
    like = [str(x) for x in ((b.get("look") or {}).get("like") or [])]     # this runs on every save)
    out["look"] = {"like": list(dict.fromkeys(x for x in like if re.fullmatch(r"[^\\/:*?\"<>|]{1,160}", x)
                                              and not x.startswith((".", "-")) and (ANALYSIS / x / "events.json").is_file()))[:3]}
    gl, seen = [], set()                             # the glossary: a word once (any case), its spelling kept
    for g in b.get("glossary") or []:
        w = _s((g or {}).get("word"), MAX["word"])
        if w and w.lower() not in seen and len(gl) < MAX["words_n"]:
            seen.add(w.lower())
            gl.append({"word": w, "say": _s(g.get("say"), MAX["say"])})
    out["glossary"] = gl
    cat, ids = [], set()
    for p in b.get("catalogue") or []:
        name = _s((p or {}).get("name"), MAX["name"])
        if not name:
            continue
        pid = str(p.get("id") or "")
        if not re.fullmatch(r"p\d{1,5}", pid) or pid in ids:
            pid = next(f"p{i}" for i in range(1, 100000) if f"p{i}" not in ids)
        ids.add(pid)
        img = str(p.get("image") or "").replace("\\", "/")              # only a picture take_import copied
        img = img if re.fullmatch(r"knowledge/local/brand/products/p\d{1,5}\.(png|jpg|webp|svg)", img) and (LAB / img).is_file() else ""
        try:
            link = _url(p.get("url"))
        except ValueError:
            link = ""
        claims = [{"text": _s(c.get("text"), 120), "proof": _s(c.get("proof"), 160)}
                  for c in (p.get("claims") or []) if isinstance(c, dict) and _s(c.get("text"), 120)][:5]
        never = list(dict.fromkeys(x for x in (_s(v, 80) for v in p.get("never") or []) if x))[:6]
        media = [m for m in (str(v or "").replace("\\", "/") for v in p.get("media") or [])
                 if re.fullmatch(rf"knowledge/local/brand/products/{pid}_m\d{{1,3}}\.(png|jpg|webp|mp4|mov|webm)", m)
                 and (LAB / m).is_file()][:PRODUCT_MEDIA_N]
        cat.append({"id": pid, "name": name, "what": _s(p.get("what"), MAX["what"]),
                    "price": _s(p.get("price"), MAX["price"]), "url": link, "image": img, "use": p.get("use") is not False,
                    "promo": _s(p.get("promo"), 40), "sponsored": p.get("sponsored") is True,
                    "benefit": _s(p.get("benefit"), 120), "claims": claims, "never": never, "media": media})
    out["catalogue"] = cat[:MAX["products"]]
    return out


def _clean_tone(t: dict) -> dict:
    """The voice in the user's own words: the sliders (0..4 or None), words to use / never to use (<= 20 each, one or
    two words), lines that sound like them (<= 5, <= 160 characters)."""
    dims = t.get("dims") or {}
    words = lambda xs: list(dict.fromkeys(w for w in (_s(x, 40) for x in (xs or [])) if w))[:20]  # noqa: E731
    return {"dims": {k: (int(dims[k]) if isinstance(dims.get(k), (int, float)) and 0 <= dims[k] <= 4 else None) for k in TONE_DIMS},
            "use": words(t.get("use")), "avoid": words(t.get("avoid")),
            "lines": [x for x in (_s(y, 160) for y in (t.get("lines") or [])) if x][:5]}


def tone_words(tone: dict) -> str:
    """The sliders in words: 'quite casual, a little funny, ...' (the middle and the unset ones left out)."""
    out = []
    for k, (lo, hi) in TONE_DIMS.items():
        v = (tone.get("dims") or {}).get(k)
        if v is None or v == 2:
            continue
        out.append({0: f"very {lo}", 1: f"rather {lo}", 3: f"rather {hi}", 4: f"very {hi}"}[v])
    return ", ".join(out)


def _add_font(g: dict) -> str | None:
    """An imported Google font (import\\fonts\\<dir>: its TTFs + licence) copied into the user's own fonts
    (library\\fonts\\<dir>, this PC only - an existing folder is used as it is); its family name, or None."""
    import shutil
    from . import fonts as F
    src = LAB / str(g.get("dir") or "")
    if not src.is_dir() or LAB not in src.resolve().parents or not list(src.glob("*.ttf")):
        return None
    dst = F.LOCAL / src.name
    if not dst.exists():
        shutil.copytree(src, dst)
    try:
        return F.read_font(sorted(dst.glob("*.ttf"))[0])["family"] or None
    except (OSError, IndexError, KeyError, ValueError):
        return None


def _font_families() -> list[dict]:
    from . import fonts as F
    try:
        return F.families()
    except OSError:
        return []


def load(path: Path = PATH) -> dict:
    try:
        return {**empty(), **json.loads(Path(path).read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return empty()


def save(body: dict, path: Path = PATH, own_sound: bool = False) -> dict:
    """Check and write the brand (a temp file + rename); returns what was saved. The sound logo is the stored one
    unless own_sound (save_sound_logo, reset, undo): the page never sets it - the job that makes one writes it while
    the page is open, and the page's next save would put its older copy back."""
    if not own_sound:
        body = {**(body or {}), "identity": {**((body or {}).get("identity") or {}),
                                             "sound_logo": (load(path).get("identity") or {}).get("sound_logo", "")}}
    data = clean(body)
    data["updated"] = time.strftime("%Y-%m-%d %H:%M")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)
    return data


def reset(path: Path = PATH) -> dict:
    """Start from zero (the user's button, 2026-10-25: "reset all data for my brand ... to try from zero"): brand.json
    is copied to brand_backups\\brand-<date>.json first, then saved empty. The logo / product pictures / fonts stay on
    disk (nothing is deleted); undo_reset() brings the copy back."""
    p = Path(path)
    if p.exists():
        d = p.parent / "brand_backups"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"brand-{time.strftime('%Y%m%d-%H%M%S')}.json").write_bytes(p.read_bytes())
    return save(empty(), path, own_sound=True)


def undo_reset(path: Path = PATH) -> dict:
    """The newest copy reset() kept, back as My Brand (checked like any save)."""
    d = Path(path).parent / "brand_backups"
    last = max(d.glob("brand-*.json"), default=None) if d.is_dir() else None
    if not last:
        raise ValueError(I18N.t("no earlier My Brand to bring back"))
    return save(json.loads(last.read_text(encoding="utf-8")), path, own_sound=True)


def save_logo(name: str, data: str, path: Path = PATH, kind: str = "") -> dict:
    """The brand's logo (a picture the user picked, sent as base64): checked (`_picture`), written as
    knowledge\\local\\brand\\logo.<ext>; brand.json points to it. kind = one of LOGO_KINDS (2026-10-26): that version,
    logo_<kind>.<ext>, in identity "logos"."""
    if kind and kind not in LOGO_KINDS:
        raise ValueError(f"no logo version '{kind[:20]}'")
    raw, ext = _picture(name, data)
    b = load(path)
    idt = b.get("identity") or {}
    if kind:
        b["identity"] = {**idt, "logos": {**(idt.get("logos") or {}), kind: _put_logo(raw, ext, kind)}}
    else:
        b["identity"] = {**idt, "logo": _put_logo(raw, ext)}
    return save(b, path)


def save_sound_logo(name: str, raw: bytes, path: Path = PATH) -> dict:
    """The brand's sound logo (0.6.0 step 10, 5c's "optional short sound logo"): a sound file the user picked or one
    ElevenLabs made - at most SOUND_LOGO_MAX_S long - written as knowledge\\local\\brand\\sound_logo.<ext>; brand.json
    points to it and the end card plays it (end_card "sound": "logo")."""
    from . import sfx as SFX
    ext = Path(str(name)).suffix.lower()
    if ext not in SOUND_EXT:
        raise ValueError(I18N.t("{file}: not a sound ({types})", file=str(name)[-60:], types=", ".join(SOUND_EXT)))
    if not 0 < len(raw) <= 10_000_000:
        raise ValueError(I18N.t("the file is empty or bigger than 10 MB"))
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    f = LOGO_DIR / f"sound_logo{ext}"
    part = f.with_name(f.name + ".part" + ext)
    part.write_bytes(raw)
    try:
        n = len(SFX.load_audio(part)) / SFX.SR
    except ValueError:
        part.unlink(missing_ok=True)
        raise ValueError(I18N.t("{file}: no sound found in it", file=str(name)[-60:])) from None
    if not 0.2 <= n <= SOUND_LOGO_MAX_S:
        part.unlink(missing_ok=True)
        raise ValueError(I18N.t("a sound logo is a few seconds long - this one is {n} s", n=f"{n:.1f}"))
    part.replace(f)
    b = load(path)
    b["identity"] = {**(b.get("identity") or {}), "sound_logo": f.relative_to(LAB).as_posix()}
    b["end_card"] = {**(b.get("end_card") or {}), "sound": "logo"}
    return save(b, path, own_sound=True)


def sound_logo_words(b: dict) -> str:
    """A first description for ElevenLabs - the user changes it before anything is made."""
    name = b.get("name") or "the brand"
    t = ((b.get("identity") or {}).get("tone") or {}).get("dims") or {}
    feel = ("playful and bright" if (t.get("funny") or 0) >= 3 or (t.get("cheeky") or 0) >= 3
            else "energetic and bold" if (t.get("excited") or 0) >= 3 else "calm, confident and premium")
    return (f"a short sonic logo for {name}, {feel}: two or three clean rising synth notes with a soft airy shimmer "
            "at the end, polished and modern, one-shot, no voice, no drums, no background music")


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two #rrggbb colours: 1 (the same) to 21 (black on white)."""
    def lum(h: str) -> float:
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return round((hi + 0.05) / (lo + 0.05), 1)


def ink_on(bg: str, ink: str | None = None) -> str:
    """The text colour for background bg: ink when it reads (READ_TEXT), else near-white or near-black, whichever
    reads better."""
    if ink and contrast(ink, bg) >= READ_TEXT:
        return ink
    return max(("#ffffff", "#111111"), key=lambda x: contrast(x, bg))


def logo_for(b: dict, bg: str | None = None, small: bool = False) -> str:
    """The logo file for a background (2026-10-26): on a dark one the light version, on a light one the dark
    version, small = the icon first; else the main logo. "" when the brand has none."""
    idt = b.get("identity") or {}
    lv = idt.get("logos") or {}
    order = (["icon"] if small else []) + ([("light" if contrast(bg, "#000000") < contrast(bg, "#ffffff") else "dark")]
                                           if bg and re.fullmatch(r"#[0-9a-f]{6}", bg) else [])
    return next((lv[k] for k in order if lv.get(k)), "") or idt.get("logo") or next(
        (lv[k] for k in LOGO_KINDS if lv.get(k)), "")


def readable(b: dict) -> list[dict]:
    """The brand's text and accent colours against its background colours (by role): [{"fg", "bg", "use": text|accent,
    "ratio", "ok"}] - text needs READ_TEXT, an accent (titles, buttons, shapes) READ_BIG."""
    cols = (b.get("identity") or {}).get("colours") or []
    bgs = [c["hex"] for c in cols if c.get("role") == "background"]
    out = []
    for c in cols:
        use = {"text": "text", "accent": "accent"}.get(c.get("role"))
        for bg in bgs if use else []:
            r = contrast(c["hex"], bg)
            out.append({"fg": c["hex"], "bg": bg, "use": use, "ratio": r, "ok": r >= (READ_TEXT if use == "text" else READ_BIG)})
    return out


def _picture(name: str, data: str, logo: bool = True) -> tuple[bytes, str]:
    """A picture the user picked (base64): PNG / JPEG / WebP by their first bytes, an SVG without scripts, at most 5 MB
    -> (bytes, extension; .jpeg = .jpg). ValueError otherwise (logo = the logo's words, else a product picture's)."""
    import base64
    ext = Path(str(name or "")).suffix.lower()
    if ext not in LOGO_EXT:
        raise ValueError(I18N.t("a logo is a PNG, JPG, WebP or SVG picture") if logo
                         else I18N.t("a product picture is a PNG, JPG, WebP or SVG picture"))
    raw = base64.b64decode(str(data or "").split(",", 1)[-1], validate=False)
    if not raw or len(raw) > 5_000_000:
        raise ValueError(I18N.t("a logo up to 5 MB") if logo else I18N.t("a picture up to 5 MB"))
    head = raw[:16]
    ok = {".png": head.startswith(b"\x89PNG"), ".jpg": head.startswith(b"\xff\xd8"), ".jpeg": head.startswith(b"\xff\xd8"),
          ".webp": head[:4] == b"RIFF" and raw[8:12] == b"WEBP"}.get(ext)
    if ext == ".svg":
        txt = raw.decode("utf-8", "replace").lower()
        ok = "<svg" in txt and not re.search(r"<script|<foreignobject|\son\w+\s*=|javascript:", txt)
    if not ok:
        raise ValueError(I18N.t("this file is not a {kind} picture", kind=ext[1:].upper()))
    return raw, ".jpg" if ext == ".jpeg" else ext


def save_product_image(pid: str, name: str, data: str, path: Path = PATH) -> dict:
    """A product's own picture (the Catalogue tab, 2026-10-25): checked like the logo, written as
    knowledge\\local\\brand\\products\\<id>.<ext>, the product points to it. ValueError for an unknown product."""
    raw, ext = _picture(name, data, logo=False)
    b = load(path)
    p = next((x for x in b.get("catalogue") or [] if x.get("id") == pid), None)
    if not p or not re.fullmatch(r"p\d{1,5}", str(pid)):
        raise ValueError(I18N.t("no product {id} in the catalogue", id=str(pid)[:20]))
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    f = PRODUCT_DIR / f"{pid}{ext}"
    f.write_bytes(raw)
    p["image"] = f.relative_to(LAB).as_posix()
    return save(b, path)


def product_facts(p: dict) -> str:
    """A product's facts for a brief (5b): its key benefit, the claims allowed with their proof, the ones never to make,
    its screenshots / recordings - "" when it has none."""
    return ((f" - key benefit: {p['benefit']}" if p.get("benefit") else "")
            + (" - claims you may make: " + "; ".join(f"\"{c['text']}\"" + (f" (proof: {c['proof']})" if c.get("proof") else "")
                                                       for c in p["claims"]) if p.get("claims") else "")
            + (" - NEVER claim: " + "; ".join(f"\"{x}\"" for x in p["never"]) if p.get("never") else "")
            + (" - its screenshots / recordings (copy one into the build folder to show it): "
               + ", ".join(f"`{m}`" for m in p["media"]) if p.get("media") else ""))


def save_product_media(pid: str, name: str, data: str, path: Path = PATH) -> dict:
    """A product's media (5b, 2026-10-26): a screenshot (PNG / JPEG / WebP, checked like a picture) or a short screen
    recording (MP4 / MOV / WebM by its first bytes, <= PRODUCT_VIDEO_MB) - knowledge\\local\\brand\\products\\
    <id>_m<n>.<ext>, added to the product's "media" (PRODUCT_MEDIA_N at most). ValueError otherwise."""
    import base64
    ext = Path(str(name or "")).suffix.lower()
    b = load(path)
    p = next((x for x in b.get("catalogue") or [] if x.get("id") == pid), None)
    if not p or not re.fullmatch(r"p\d{1,5}", str(pid)):
        raise ValueError(I18N.t("no product {id} in the catalogue", id=str(pid)[:20]))
    if len(p.get("media") or []) >= PRODUCT_MEDIA_N:
        raise ValueError(I18N.t("{n} pictures or recordings a product at most", n=PRODUCT_MEDIA_N))
    if ext in (".mp4", ".mov", ".webm"):
        raw = base64.b64decode(str(data or "").split(",", 1)[-1], validate=False)
        if not raw or len(raw) > PRODUCT_VIDEO_MB * 1_000_000:
            raise ValueError(I18N.t("a recording up to {n} MB", n=PRODUCT_VIDEO_MB))
        if not (raw[4:8] == b"ftyp" or raw[:4] == b"\x1aE\xdf\xa3"):
            raise ValueError(I18N.t("this file is not a {kind} recording", kind=ext[1:].upper()))
    else:
        raw, ext = _picture(name, data, logo=False)
        if ext == ".svg":
            raise ValueError(I18N.t("a screenshot is a PNG, JPG or WebP picture"))
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    n = 1 + max([int(m) for m in re.findall(rf"{pid}_m(\d+)\.", " ".join(x.name for x in PRODUCT_DIR.iterdir()))] or [0])
    f = PRODUCT_DIR / f"{pid}_m{n}{ext}"
    f.write_bytes(raw)
    p["media"] = [*(p.get("media") or []), f.relative_to(LAB).as_posix()]
    return save(b, path)


def _put_logo(raw: bytes, ext: str, kind: str = "") -> str:
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    f = LOGO_DIR / f"logo{'_' + kind if kind else ''}{'.jpg' if ext == '.jpeg' else ext}"
    f.write_bytes(raw)
    return f.relative_to(LAB).as_posix()


def take_import(picks: dict, path: Path = PATH, found: dict | None = None) -> dict:
    """Import from your website: the items the user ticked in the found list copied into My Brand - picks =
    {"name": bool, "about": bool, "colours": [hex], "logo": "<a found logo's file>", "fonts": {"heading", "body"},
    "pages": [platform], "products": [index in found.products]}. Only what found.json holds can come in; colours,
    pages and products are added to what is there (a product already in the catalogue by name is left as it is)."""
    from . import siteread as SR
    f = found if found is not None else SR.load()
    if not f:
        raise ValueError(I18N.t("nothing imported yet - press Import from your website first"))
    picks, b = picks or {}, load(path)
    if picks.get("name") and f.get("name"):
        b["name"] = f["name"]
    if picks.get("about") and f.get("about"):
        b["about"] = f["about"]
    idt = b.setdefault("identity", {})
    have = {c["hex"] for c in idt.get("colours") or []}
    for c in f.get("colours") or []:
        if c["hex"] in (picks.get("colours") or []) and c["hex"] not in have and len(idt.setdefault("colours", [])) < MAX["colours"]:
            idt["colours"].append({"hex": c["hex"], "name": "", "role": c.get("role") or ""})
            have.add(c["hex"])
    lg = next((x for x in f.get("logos") or [] if x.get("file") and x["file"] == picks.get("logo")), None)
    if lg:
        src = LAB / lg["file"]
        if src.is_file() and src.suffix.lower() in LOGO_EXT:
            idt["logo"] = _put_logo(src.read_bytes(), src.suffix.lower())
    lib = {x["library"] for x in f.get("fonts") or [] if x.get("library")}
    fo = dict(idt.get("fonts") or {})
    for k in ("heading", "body"):
        want = (picks.get("fonts") or {}).get(k)
        if want in lib:
            fo[k] = want
        elif want:                                   # a free Google font the site uses: into the user's own fonts first
            g = next((x["google"] for x in f.get("fonts") or [] if x["family"] == want and x.get("google")), None)
            fam = _add_font(g) if g else None
            if fam:
                fo[k] = fam
    idt["fonts"] = fo
    pages = list(b.get("pages") or [])
    for pg in f.get("pages") or []:
        if pg["platform"] in (picks.get("pages") or []):
            old = next((x for x in pages if x["platform"] == pg["platform"]), None)
            if old:
                old["url"] = pg["url"]
            else:
                pages.append({"platform": pg["platform"], "url": pg["url"], "cta": ""})
    b["pages"] = pages
    cat = list(b.get("catalogue") or [])
    names = {p["name"].lower() for p in cat}
    ids = {p["id"] for p in cat}
    prods = f.get("products") or []
    for i in picks.get("products") or []:
        if not isinstance(i, int) or not 0 <= i < len(prods) or prods[i]["name"].lower() in names:
            continue
        p = prods[i]
        pid = next(f"p{n}" for n in range(1, 100000) if f"p{n}" not in ids)
        ids.add(pid)
        names.add(p["name"].lower())
        img = ""
        src = LAB / p["image"] if p.get("image") else None
        if src and src.is_file() and src.suffix.lower() in (".png", ".jpg", ".webp", ".svg"):
            PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
            dst = PRODUCT_DIR / f"{pid}{src.suffix.lower()}"
            dst.write_bytes(src.read_bytes())
            img = dst.relative_to(LAB).as_posix()
        cat.append({"id": pid, "name": p["name"], "what": p.get("what", ""), "price": p.get("price", ""),
                    "url": p.get("url", ""), "image": img, "use": True})
    b["catalogue"] = cat
    site = b.setdefault("site", {})
    site["read"] = f.get("at")
    if picks.get("text") and f.get("text"):          # what the website says: kept as a file Claude reads for facts
        SITE_TEXT.parent.mkdir(parents=True, exist_ok=True)
        SITE_TEXT.write_text(f"# What {f.get('site') or 'the website'} says (read {f.get('at')})\n\n" + f["text"].strip() + "\n",
                             encoding="utf-8")
        site["text"] = SITE_TEXT.relative_to(LAB).as_posix()
    if not site.get("url"):
        site["url"] = f.get("url", "")
    return save(b, path)


def caption_look(b: dict | None = None) -> tuple[str, dict] | None:
    """My Brand's caption style as the captions graphic takes it: (the ready look's id, the values on top of it) -
    None when the brand has none (nothing set)."""
    cp = ((b if b is not None else load()).get("identity") or {}).get("captions") or {}
    if not any(v not in ("", None, 0) for v in cp.values()):
        return None
    v: dict = {}
    if cp.get("size") in CAPTION_SIZE:                   # the look's own size x the brand's (3c)
        try:
            fs = json.loads(CAPTION_PRESETS.read_text(encoding="utf-8"))[cp.get("look") or "classic"]["values"]["font_size"]
            v["font_size"] = round(fs * CAPTION_SIZE[cp["size"]])
        except (OSError, ValueError, KeyError):
            pass
    if cp.get("font"):
        v["font"] = cp["font"]
    if cp.get("case") == "upper":
        v.update(uppercase=True, first_capital=False)
    elif cp.get("case") == "sentence":
        v.update(uppercase=False, first_capital=True)
    if cp.get("color"):
        v["color"] = cp["color"]
    if cp.get("highlight"):
        v["highlight_color"] = cp["highlight"]
    if cp.get("motion") and cp.get("look") != "keyword":   # (the Keyword look is its own motion: word by word)
        v["style"] = cp["motion"]
    if cp.get("position") in CAPTION_Y:
        v["y"], v["y_upright"] = CAPTION_Y[cp["position"]]
    if isinstance(cp.get("box"), bool):
        v["box"] = cp["box"]
    return (cp.get("look") or "classic"), v


def caption_words(b: dict | None = None) -> int | None:
    """My Brand's words per caption line (3c, 2026-10-26) - `overlay.py captions --brand` groups by it; None = the
    look's own grouping."""
    n = (((b if b is not None else load()).get("identity") or {}).get("captions") or {}).get("words")
    return n if n in CAPTION_WORDS else None


def product_card_values(b: dict, p: dict) -> dict:
    """Product motion (0.6.0 step 5): the Motion Graphics template `product-card`'s settings for product p of brand b -
    its words, the button (the website, else the first page's handle), the brand's colours by role (text = ink,
    background = paper, accent = signal; no roles = the first colour is the accent) and fonts. The pictures
    (product_media, logo_media) are set when they are copied into the graphic (assets\\media\\)."""
    site = re.sub(r"^https?://(www\.)?", "", (b.get("site") or {}).get("url") or "").rstrip("/")
    page = next((pg for pg in b.get("pages") or [] if pg.get("url")), None)
    handle = "@" + page["url"].rstrip("/").rsplit("/", 1)[-1].lstrip("@") if page else ""
    return {"name": p.get("name", ""), "what": p.get("what", ""), "price": p.get("price", ""), "cta": site or handle,
            **look_values(b)}


def look_values(b: dict) -> dict:
    """The brand as a look-aware template's tokens (2026-10-26; product-card, the Generator's quick draft): its colours
    by role (text = ink, background = paper, accent = signal; no roles = the first colour is the accent; ink always
    reads on paper) and fonts (heading = display_font, body = body_font + accent_font)."""
    idt = b.get("identity") or {}
    cols = idt.get("colours") or []
    role = {c.get("role"): c["hex"] for c in reversed(cols) if c.get("role")}
    v = {}
    if role:
        for k, r in (("ink", "text"), ("paper", "background")):
            if role.get(r):
                v[k] = role[r]
        acc = role.get("accent") or role.get("neutral") or role.get("text")
        if acc:
            v["signal"] = acc
    elif cols:
        v["signal"] = cols[0]["hex"]
    if v.get("paper"):                                   # 3f: only words that read on the card
        v["ink"] = ink_on(v["paper"], v.get("ink"))
    fo = idt.get("fonts") or {}
    if fo.get("heading"):
        v["display_font"] = fo["heading"]
    if fo.get("body"):
        v["body_font"] = v["accent_font"] = fo["body"]
    return v


def worked(n: int = 5) -> dict:
    """Hooks, endings and titles that worked (3j, 2026-10-26) - only from the user's own ratings, never a generic
    list: a script of the prompt library rated good, or one a video rated good overall was made from (its
    build\\made_from.json + outcome.json), gives its HOOK part's first line and its CTA part's (else its first / last
    line); a title rated good the title chosen (else its first). Newest first, n of each.
    -> {"hooks": [{"text", "from"}], "ctas", "titles"}."""
    from . import script as SC
    prompts = LAB / "knowledge" / "local" / "prompts"
    good_videos = set()
    for o in (LAB / "projects").glob("*/build/outcome.json"):
        try:
            if ((json.loads(o.read_text(encoding="utf-8")).get("aspects") or {}).get("overall") or {}).get("rating") != "good":
                continue
            mf = json.loads((o.parent / "made_from.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        good_videos |= {m.get("id") for m in mf if isinstance(m, dict) and m.get("kind") == "prompt"}
    rows = []
    for f in list(prompts.glob("script/*.json")) + list(prompts.glob("title/*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (r.get("result") or {}).get("rating") == "good" or r.get("id", f.stem) in good_videos:
            rows.append((str(r.get("updated") or r.get("date") or ""), f.parent.name, r.get("id", f.stem), r))
    out = {"hooks": [], "ctas": [], "titles": []}
    for _, kind, pid, r in sorted(rows, key=lambda x: x[0], reverse=True):
        if kind == "title":                              # the title they chose, else the first one written
            ttl = r.get("chosen") or next((x.get("text") for x in r.get("titles") or [] if isinstance(x, dict)), "")
            if ttl and len(out["titles"]) < n:
                out["titles"].append({"text": str(ttl).strip(), "from": pid})
            continue
        parts = [c for c in SC.cue_cards(r.get("text", "")) if c["lines"]]
        if not parts:
            continue
        hook = next((c for c in parts if c["head"].upper().startswith("HOOK")), parts[0])["lines"][0]
        cta = next((c for c in parts if c["head"].upper().startswith("CTA")), parts[-1])["lines"][-1]
        for k, txt in (("hooks", hook), ("ctas", cta)):
            if txt and len(out[k]) < n and txt not in {x["text"] for x in out[k]}:
                out[k].append({"text": txt.strip(), "from": pid})
    return out


def end_card(b: dict, preview: bool = False) -> dict | None:
    """The signature end card (5c, 2026-10-26): My Brand's pick as a Motion Graphics template + its settings from the
    brand - its colours by role (words always readable), the heading font where the template offers it, the logo
    version that reads on its colour, the name, the sign-off line and the website (else the first page's handle).
    -> {"template", "values", "logo": the lab path of the logo picture or "", "logo_key": the setting it goes in,
    "sound": the sound logo's lab path when the end card plays it, else ""}.
    preview = the logo as the app's /files/ address in the values (My Brand's live preview); else the value is
    assets/media/<its file> - copy the picture there. None when no style is picked."""
    from . import overlay_settings as OS
    ec = b.get("end_card") or {}
    tid = END_STYLES.get(ec.get("style"))
    if not tid:
        return None
    lv = look_values(b)
    paper, signal = lv.get("paper") or "#111113", lv.get("signal") or "#ff6fae"
    ink = ink_on(paper, lv.get("ink"))
    name, line = b.get("name") or "", ec.get("line") or ""
    site = re.sub(r"^https?://(www\.)?", "", (b.get("site") or {}).get("url") or "").rstrip("/")
    page = next((pg for pg in b.get("pages") or [] if pg.get("url")), None)
    where = site or ("@" + page["url"].rstrip("/").rsplit("/", 1)[-1].lstrip("@") if page else "")
    key = END_LOGO_KEY.get(tid)
    logo = logo_for(b, signal if tid == "logo-reveal" else None, small=tid == "end-screen") if key else ""
    if tid == "logo-reveal":
        v = {"mark": (name or where or "?")[:1].upper(), "name": name.upper(), "tagline": line or where, "size": 1.8,
             "mark_color": signal, "letter_color": ink_on(signal), "text_color": ink, "bg": paper, "background": True}
        # (size 1.8: an end card's logo fills the frame - local-make-25, a wide logo in the mark came out tiny at 1)
    elif tid == "title-card":
        v = {"look": "product", "top": name, "main": line or name, "bottom": "", "button": where, "color": ink,
             "accent": signal, "bg": paper, "background": True, "size": 1.25}
    else:
        v = {"channel": name or where, "accent": signal, "c1": paper, "c2": paper, "background": True,
             **({"title": line} if line else {})}
    if lv.get("display_font"):
        v["font"] = lv["display_font"]
    if tid == "title-card" and lv.get("body_font"):
        v["text_font"] = lv["body_font"]
    if logo:
        v[key] = "/files/" + logo if preview else "assets/media/" + Path(logo).name
    v, _ = OS.check(OS.declared(LAB / "tools" / "overlays" / "motion" / tid), v)   # a font it does not offer: its own
    snd = (b.get("identity") or {}).get("sound_logo") or ""
    snd = snd if ec.get("sound") == "logo" and snd and (LAB / snd).is_file() else ""
    return {"template": tid, "values": v, "logo": logo if key in v else "", "logo_key": key or "", "sound": snd}


GOAL_WORDS = {"sell": "sell", "personal_brand": "build a personal brand", "community": "build a community",
              "inform": "inform"}


def filled(b: dict) -> bool:
    """Whether My Brand holds anything to make a video with."""
    g, idt = b.get("goal") or {}, b.get("identity") or {}
    return bool(b.get("name") or b.get("about") or g.get("picks") or g.get("words") or b.get("audience")
                or idt.get("colours") or idt.get("voice") or idt.get("logo") or any((idt.get("fonts") or {}).values())
                or (b.get("site") or {}).get("url") or b.get("pages") or (b.get("look") or {}).get("like")
                or caption_look(b) or b.get("glossary") or b.get("pillars") or b.get("catalogue")
                or tone_words(idt.get("tone") or {}) or any((idt.get("tone") or {}).get(k) for k in ("use", "avoid", "lines")))


def glossary_words(b: dict | None = None) -> list[str]:
    """The glossary's words as written (captions' speech to text takes them as names)."""
    return [g["word"] for g in (b if b is not None else load()).get("glossary") or [] if g.get("word")]


def snapshot(path: Path = PATH) -> dict | None:
    """For my brand (0.6.0): the brand as it is now, for a request - only the products the user lets Claude use;
    None when My Brand is empty."""
    b = load(path)
    if not filled(b):
        return None
    return {"name": b.get("name", ""), "about": b.get("about", ""), "goal": b["goal"], "audience": b["audience"],
            "identity": b["identity"], "site": {"url": b["site"].get("url", "")},
            "pages": [p for p in b.get("pages") or [] if p.get("url")], "look": b.get("look") or {"like": []},
            "glossary": b.get("glossary") or [], "pillars": b.get("pillars") or [],
            "end_card": b.get("end_card") or {"style": "", "line": ""}, "worked": worked(),
            "site_text": (b.get("site") or {}).get("text", ""),
            "catalogue": [p for p in b.get("catalogue") or [] if p.get("use") is not False], "as_of": b.get("updated")}


def brief_lines(b: dict, purpose: str = "video") -> list[str]:
    """For my brand: a brief's section - the brand's facts, then what to do with them. purpose = "video" (an edit,
    a video from zero) or "words" (a script, a title)."""
    g, idt, site = b.get("goal") or {}, b.get("identity") or {}, b.get("site") or {}
    goals = [GOAL_WORDS[p] for p in g.get("picks") or [] if p in GOAL_WORDS]
    L = ["The user ticked **For my brand**: make it theirs. The facts are My Brand's (knowledge\\local\\brand.json) as "
         f"they were when they asked ({b.get('as_of') or 'today'})."]
    if b.get("name") or b.get("about"):
        L.append("- The brand: " + (b.get("name") or "-") + (f" - {b['about']}" if b.get("about") else ""))
    if goals or g.get("words"):
        L.append("- Goal on social media: " + (" and ".join(goals) or "-")
                 + (f" - in their words: \"{g['words']}\"" if g.get("words") else ""))
    if b.get("audience"):
        L.append("- Who it is for: " + "; ".join(b["audience"]))
    if idt.get("voice"):
        L.append(f"- Tone of voice: {idt['voice']}")
    tn = idt.get("tone") or {}
    if tone_words(tn):
        L.append(f"- How they sound: {tone_words(tn)}")
    if tn.get("use"):
        L.append("- Words they use: " + ", ".join(tn["use"]))
    if tn.get("avoid"):
        L.append("- Words they NEVER use (never write them): " + ", ".join(tn["avoid"]))
    if tn.get("lines"):
        L += ["- Lines that sound like them (match this voice - do not copy them):", *[f"  > {x}" for x in tn["lines"]]]
    wk = b.get("worked") or {}
    if any(wk.get(k) for k in ("hooks", "ctas", "titles")):         # 3j: from their own ratings only
        L.append("- What worked for them (their own ratings - match the shape and the energy, never reuse the words): "
                 + "; ".join(f"{lab} " + " / ".join(f"\"{x['text']}\" ({x['from']})" for x in wk[k])
                             for k, lab in (("hooks", "hooks"), ("ctas", "endings"), ("titles", "titles")) if wk.get(k)))
    if b.get("pillars"):
        L.append("- Their content pillars (what they post about): " + "; ".join(
            p["name"] + (f" - {p['what']}" if p.get("what") else "") + (f" (series: {p['series']})" if p.get("series") else "")
            for p in b["pillars"]))
    if b.get("site_text"):
        L.append(f"- What their website says: `{b['site_text']}` - read it for facts (services, prices, who they are, "
                 "where); its marketing words are not their voice")
    if b.get("glossary"):
        L.append("- Names and words - spell them exactly like this, same capitals, never translated: "
                 + ", ".join(g["word"] + (f" (said \"{g['say']}\")" if g.get("say") else "") for g in b["glossary"]))
    if idt.get("colours"):
        L.append("- Brand colours: " + ", ".join(c["hex"] + (f" ({', '.join(x for x in (c.get('role'), c.get('name')) if x)})"
                                                             if c.get("role") or c.get("name") else "")
                                                 for c in idt["colours"]))
        rd = readable(b)
        if rd:
            L.append("- Which words read (contrast; text needs 4.5, titles and accents 3): " + "; ".join(
                f"{r['fg']} {r['use']} on {r['bg']} {r['ratio']}:1 " + ("reads" if r["ok"] else
                f"does NOT read - on {r['bg']} use {ink_on(r['bg'])} for {'text' if r['use'] == 'text' else 'it'}")
                for r in rd))
    fo = {k: v for k, v in (idt.get("fonts") or {}).items() if v}
    if fo:
        L.append("- Brand fonts (the lab's font library): " + ", ".join(
            f"{v} for {'titles and headings' if k == 'heading' else 'body text and captions'}" for k, v in fo.items()))
    lv = {k: f for k, f in (idt.get("logos") or {}).items() if f}
    if idt.get("logo") or lv:
        L.append("- Logo: " + "; ".join(([f"`{idt['logo']}` (the main one)"] if idt.get("logo") else [])
                                        + [f"`{f}` ({LOGO_USE[k]})" for k, f in lv.items()])
                 + " - in a template's logo setting (or `:brand:` in a text) write `brand`: the graphic draws the version "
                   "that reads on its background by itself (`brand/icon` = the icon); elsewhere copy the one that reads "
                   "into the video's build folder; never change it")
    ecd = end_card(b) if purpose == "video" else None
    if ecd:
        L.append("- **Their signature end card** (picked on My Brand - the video's last scene, never before the hook): "
                 f"`tools\\overlay.py new build\\overlays\\end_card --from {ecd['template']} --values "
                 f"{json.dumps(ecd['values'], ensure_ascii=False)}` (pass it as one argument from Python, not through a "
                 "shell), then `overlay.py fit` to the video's size" + (
                     f"; copy `{ecd['logo']}` into the graphic's `assets\\media\\` (its `{ecd['logo_key']}` points there)"
                     if ecd["logo"] else "") + (
                     f"; its sound = their sound logo: the plan's \"sfx\": {{\"logo\": \"{(LAB / ecd['sound']).as_posix()}\"}} "
                     "(it plays where the end card's own sounds would, instead of them)" if ecd.get("sound") else ""))
    if site.get("url"):
        L.append(f"- Website: {site['url']}")
    pages = [p for p in b.get("pages") or [] if p.get("url")]
    if pages:
        L.append("- Their pages: " + "; ".join(PLATFORMS.get(p["platform"], p["platform"]) + " " + p["url"]
                                              + (f" (call to action: \"{p['cta']}\")" if p.get("cta") else "") for p in pages))
    cap = caption_look(b)
    if cap and purpose == "video":
        L.append(f"- Caption style (theirs - every caption): `tools\\overlay.py captions <folder> --from <words> --brand` "
                 f"(the look `{cap[0]}` with {json.dumps(cap[1], ensure_ascii=False)} on top"
                 + (f", {caption_words(b)} words a line at most" if caption_words(b) else "")
                 + "); never another look unless the request asks.")
    look = (b.get("look") or {}).get("like") or []
    if look and purpose == "video":
        L.append("- Their editing look (videos they analysed, chosen as the brand's pacing, transitions and grade): "
                 + ", ".join(f"`{x}`" for x in look) + " - when the request picked no references, take the style from "
                 "these (`tools\\style.py` with them, the skill's by_feel.md); when it picked some, those come first.")
    from . import moodboard as MB                       # 0.6.0 step 7: the pictures they chose as the brand's look
    L += MB.card_lines()
    prods = [p for p in b.get("catalogue") or [] if p.get("use") is not False]
    if prods:
        L.append("- Products you may show (only these; each price exactly as written):")
        L += [f"  - {p['name']}" + (f" - {p['what']}" if p.get("what") else "") + (f" - {p['price']}" if p.get("price")
              else "") + (f" - {p['url']}" if p.get("url") else "") + (f" - promo code {p['promo']}" if p.get("promo") else "")
              + (" - a PAID PARTNERSHIP: say it is an ad, on screen ('ad' / 'paid partnership') and in words, and tick "
                 "the platform's paid-partnership label when posting" if p.get("sponsored") else "")
              + (f" - picture `{p['image']}`" if p.get("image") else "") + product_facts(p) for p in prods]
    if any(p.get("benefit") or p.get("claims") for p in prods):
        L.append("  (Say only what a product's facts say - its key benefit and the claims listed, each backed by its proof; "
                 "never a feature, a number or a result that is not there, never a claim it says NEVER.)")
    if purpose == "video":
        L.append("- **What to do**: the brand colours are the palette of every title, caption and graphic unless the "
                 "request picked a palette - by their role where they have one (accent = highlights, buttons, the word "
                 "that matters; background / text = cards and words on them; neutral = panels, lines), else the first "
                 "= the main accent; words only in colours that read on their background (the contrast line); "
                 + LOGO_WHERE_DO.get(idt.get("logo_where"), "the logo on the end card (and small in a corner where it "
                                     "covers nothing)") + "; the brand fonts for titles and captions; the website - or the "
                 "page of the platform the video is for, with its call to action - at the end; words on screen in "
                 "its tone of voice, for its audience; end the way its goal asks - sell: a product, its price and the "
                 "website; a personal brand: the person's name or handle; a community: a question that invites "
                 "comments; inform: the one takeaway. A product only from the list - never an invented price.")
    else:
        L.append("- **What to do**: write in its tone of voice, for its audience, toward its goal; a product only "
                 "from the list (each price as written, none invented); the website in the call to action when the "
                 "goal is to sell, else the page of the platform it is for (with its call to action, if it has one).")
    return L


def selfcheck() -> dict:
    """Known answers for clean / save / load. {passed, seconds, lines}."""
    import tempfile
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    c = clean({"goal": {"picks": ["sell", "fly", "inform"], "words": "  max   transparency "},
               "audience": ["cooks at home", "cooks at home", "", "x" * 200],
               "identity": {"colours": [{"hex": "#2EAA5C", "name": "green"}, {"hex": "red"}], "voice": "close"},
               "site": {"url": "kutxiletto.com"},
               "catalogue": [{"name": "Origin", "price": "29,90 €"}, {"name": ""}, {"id": "p1", "name": "Pioneer", "use": False}],
               "secret": "dropped"})
    case("clean: known goals only, words trimmed", c["goal"] == {"picks": ["sell", "inform"], "words": "max transparency"})
    case("clean: audience de-duplicated, empties out, 80 characters at most",
         c["audience"][0] == "cooks at home" and len(c["audience"]) == 2 and len(c["audience"][1]) == 80)
    case("clean: a colour must be #rrggbb (lower case), its role one of the four",
         c["identity"]["colours"] == [{"hex": "#2eaa5c", "name": "green", "role": ""}]
         and clean({"identity": {"colours": [{"hex": "#ffffff", "role": "accent"}, {"hex": "#000000", "role": "boss"}]}})
         ["identity"]["colours"] == [{"hex": "#ffffff", "name": "", "role": "accent"}, {"hex": "#000000", "name": "", "role": ""}])
    case("clean: a bare domain becomes https://", c["site"]["url"] == "https://kutxiletto.com")
    case("clean: a product needs a name; ids unique; use defaults to yes",
         [(p["id"], p["name"], p["use"]) for p in c["catalogue"]] == [("p1", "Origin", True), ("p2", "Pioneer", False)])
    case("clean: unknown keys dropped", "secret" not in c)
    try:
        clean({"site": {"url": "javascript:alert(1)"}})
        bad = False
    except ValueError:
        bad = True
    case("clean: not a web address is refused", bad)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "brand.json"
        s = save({"audience": ["a"]}, p)
        case("save + load: the same brand back, with its date", load(p) == s and s["updated"] and not list(Path(td).glob("*.tmp")))
        case("load: no file = an empty brand", load(Path(td) / "none.json") == empty())
        save({"identity": {"colours": [{"hex": "#2eaa5c", "name": "green"}], "voice": "close"},
              "site": {"url": "shop.example"}, "catalogue": [{"name": "Origin", "price": "29,90 €"},
                                                            {"name": "Hidden", "use": False}]}, p)
        snap = snapshot(p)
        text = "\n".join(brief_lines(snap))
        case("For my brand: the snapshot leaves out a product switched off; the brief names colours, site, prices",
             [x["name"] for x in snap["catalogue"]] == ["Origin"] and "#2eaa5c (green)" in text
             and "https://shop.example" in text and "Origin - 29,90 €" in text and "Hidden" not in text)
        case("an empty My Brand: no snapshot", snapshot(Path(td) / "none.json") is None)
        c = clean({"pages": [{"platform": "youtube", "url": "youtube.com/@riftshoots/videos", "cta": " subscribe "},
                             {"platform": "youtube", "url": "https://www.youtube.com/@other"},
                             {"platform": "myspace", "url": "https://myspace.com/x"}, {"platform": "tiktok", "url": ""}],
                   "identity": {"fonts": {"heading": "Inter", "body": "Comic Sans of Doom"}}})
        case("clean: a page = its profile's address (https, /videos cut), one per platform, unknown platforms out",
             c["pages"] == [{"platform": "youtube", "url": "https://youtube.com/@riftshoots", "cta": "subscribe"},
                            {"platform": "tiktok", "url": "", "cta": ""}])
        case("clean: fonts only from the lab's font library", c["identity"]["fonts"] == {"heading": "Inter", "body": ""})
        cc = clean({"identity": {"captions": {"look": "clean_box", "font": "Inter", "case": "upper", "color": "#FFFFFF",
                                              "highlight": "red", "motion": "pop", "position": "top", "box": False}}})
        pv = product_card_values({"site": {"url": "https://riftshoots.com/"}, "identity": {
            "colours": [{"hex": "#0e0e10", "role": "background"}, {"hex": "#ecebe8", "role": "text"}, {"hex": "#3d4553", "role": "neutral"}],
            "fonts": {"heading": "Instrument Sans", "body": "IBM Plex Mono"}}}, {"name": "Music video", "price": "200 €"})
        case("product motion: the card's settings from My Brand - its words, the website as the button, colours by role, fonts",
             pv == {"name": "Music video", "what": "", "price": "200 €", "cta": "riftshoots.com", "ink": "#ecebe8", "paper": "#0e0e10",
                    "signal": "#3d4553", "display_font": "Instrument Sans", "body_font": "IBM Plex Mono", "accent_font": "IBM Plex Mono"}
             and product_card_values({"pages": [{"url": "https://www.instagram.com/riftshoots"}],
                                      "identity": {"colours": [{"hex": "#ff6600"}]}}, {"name": "X"})["cta"] == "@riftshoots")
        vv = clean({"identity": {"tone": {"dims": {"casual": 4, "funny": 2, "cheeky": 9, "excited": 1}, "use": ["vibe", "vibe", ""],
                                          "avoid": ["synergy"], "lines": ["We shoot it like a film.", "", "x" * 300]}},
                   "pillars": [{"name": "Behind the scenes", "series": "Day N on set"}, {"name": "behind the scenes"}, {"name": ""}],
                   "catalogue": [{"name": "Music video", "promo": "RIFT10", "sponsored": True}]})
        vt = "\n".join(brief_lines({**vv, "pillars": vv["pillars"]}, "words"))
        case("the voice in their own words, pillars, a product's promo code and paid partnership - checked and in the brief",
             vv["identity"]["tone"]["dims"] == {"casual": 4, "funny": 2, "cheeky": None, "excited": 1}
             and vv["identity"]["tone"]["use"] == ["vibe"] and len(vv["identity"]["tone"]["lines"]) == 2
             and vv["pillars"] == [{"name": "Behind the scenes", "what": "", "series": "Day N on set"}]
             and "How they sound: very casual, rather calm" in vt and "NEVER use (never write them): synergy" in vt
             and "(series: Day N on set)" in vt and "promo code RIFT10" in vt and "PAID PARTNERSHIP" in vt)
        gg = clean({"glossary": [{"word": " RIFT ", "say": "rift"}, {"word": "rift"}, {"word": ""}, {"word": "Robert Iftimie"}]})
        case("the glossary: a word once (any case), its spelling kept; in the brief for scripts too",
             gg["glossary"] == [{"word": "RIFT", "say": "rift"}, {"word": "Robert Iftimie", "say": ""}]
             and glossary_words(gg) == ["RIFT", "Robert Iftimie"]
             and 'RIFT (said "rift"), Robert Iftimie' in "\n".join(brief_lines(gg, "words")))
        case("the caption style: unknown values dropped; the graphic's values = the look + the brand's choices on top",
             cc["identity"]["captions"]["highlight"] == "" and caption_look(cc) == (
                 "clean_box", {"font": "Inter", "uppercase": True, "first_capital": False, "color": "#ffffff",
                               "style": "pop", "y": 16, "y_upright": 20, "box": False})
             and caption_look(clean({})) is None)
        cw = clean({"identity": {"captions": {"look": "clean_box", "words": "2", "size": "xl"}}})
        case("the caption style's words per line and size (3c): 2 words a line, the look's own size x 1.5; a bad "
             "value = the look's own", caption_words(cw) == 2 and caption_look(cw)[1].get("font_size") == round(
                 json.loads(CAPTION_PRESETS.read_text(encoding="utf-8"))["clean_box"]["values"]["font_size"] * 1.5)
             and clean({"identity": {"captions": {"words": 5, "size": "huge"}}})["identity"]["captions"]["words"] == 0
             and caption_words(clean({})) is None)
        case("clean: the editing look keeps only videos analysed on this PC (a made-up or unsafe name dropped)",
             clean({"look": {"like": ["no such analysis zz", "..\\..\\x", ""]}})["look"] == {"like": []})
        try:
            clean({"pages": [{"platform": "instagram", "url": "https://www.tiktok.com/@rift"}]})
            bad = False
        except ValueError:
            bad = True
        case("clean: another platform's address on a page is refused", bad)
        found = {"url": "https://rift.example/", "at": "2026-10-25 22:00", "name": "RIFT", "about": "Music videos.",
                 "colours": [{"hex": "#0e0e10"}, {"hex": "#2eaa5c"}, {"hex": "#ecebe8"}],
                 "fonts": [{"family": "Inter", "library": "Inter"}, {"family": "Instrument Sans", "library": None}],
                 "logos": [], "pages": [{"platform": "instagram", "url": "https://www.instagram.com/riftshoots"}],
                 "products": [{"name": "Music video", "what": "One day of filming", "price": "200 €",
                               "url": "https://rift.example/mv", "image": None},
                              {"name": "Origin", "price": "1 €"}, {"name": "Reel", "price": "50 €"}]}
        save({"identity": {"colours": [{"hex": "#2eaa5c", "name": "green"}]}, "catalogue": [{"name": "origin"}]}, p)
        r = take_import({"name": True, "about": False, "colours": ["#0e0e10", "#2eaa5c"], "pages": ["instagram"],
                         "fonts": {"heading": "Inter", "body": "Instrument Sans"}, "products": [0, 1, 9, "x"]}, p, found)
        case("take_import: only what was ticked - the name, colours added (one already there kept with its name), "
             "a library font only, the page, new products (one already there by name left alone, bad indexes ignored)",
             r["name"] == "RIFT" and r["about"] == "" and [c["hex"] for c in r["identity"]["colours"]] == ["#2eaa5c", "#0e0e10"]
             and r["identity"]["colours"][0]["name"] == "green" and r["identity"]["fonts"] == {"heading": "Inter", "body": ""}
             and r["pages"] == [{"platform": "instagram", "url": "https://www.instagram.com/riftshoots", "cta": ""}]
             and [(x["id"], x["name"], x["price"], x["url"]) for x in r["catalogue"]]
             == [("p1", "origin", "", ""), ("p2", "Music video", "200 €", "https://rift.example/mv")]
             and r["site"] == {"url": "https://rift.example/", "read": "2026-10-25 22:00", "text": ""})
        before = load(p)
        z = reset(p)
        case("reset: My Brand empty, the old one kept as a copy", not filled(z) and len(list((Path(td) / "brand_backups").glob("brand-*.json"))) == 1)
        back = undo_reset(p)
        case("undo_reset: the copy back as it was", {k: v for k, v in back.items() if k != "updated"}
             == {k: v for k, v in before.items() if k != "updated"})
        text = "\n".join(brief_lines(snapshot(p)))
        case("For my brand: the brief names the brand, its fonts, its pages and a product's link",
             "- The brand: RIFT" in text and "Inter for titles and headings" in text
             and "Instagram https://www.instagram.com/riftshoots" in text and "Music video - One day of filming - 200 € - https://rift.example/mv" in text)
    # 3f (2026-10-26): logo versions, where the logo goes, colours that read
    lc = clean({"identity": {"logos": {"light": "knowledge/local/brand/nope.png", "dark": "C:/x/logo_dark.png", "boss": "x"},
                             "logo_where": "corner"}})["identity"]
    case("clean: a logo version only from save_logo (else empty), where the logo goes one of three",
         lc["logos"] == {"light": "", "dark": "", "icon": ""} and lc["logo_where"] == "corner"
         and clean({"identity": {"logo_where": "everywhere"}})["identity"]["logo_where"] == "")
    case("contrast: black on white 21, the same colour 1; ink_on keeps a readable ink, else white / black",
         contrast("#000000", "#ffffff") == 21.0 and contrast("#2eaa5c", "#2eaa5c") == 1.0
         and ink_on("#0e0e10", "#ecebe8") == "#ecebe8" and ink_on("#0e0e10", "#1a1a1a") == "#ffffff"
         and ink_on("#f4f1ea", "#ffff00") == "#111111")
    lb = {"identity": {"logo": "m.png", "logos": {"light": "l.png", "dark": "d.png", "icon": "i.png"}}}
    case("logo_for: the light version on a dark background, the dark one on a light background, the icon when small",
         logo_for(lb, "#0e0e10") == "l.png" and logo_for(lb, "#f4f1ea") == "d.png" and logo_for(lb, None, True) == "i.png"
         and logo_for(lb) == "m.png" and logo_for({"identity": {"logo": "", "logos": {"dark": "d.png"}}}) == "d.png")
    rb = {"identity": {"colours": [{"hex": "#0e0e10", "role": "background"}, {"hex": "#1a1a1a", "role": "text"},
                                   {"hex": "#ff6600", "role": "accent"}], "logo_where": "none"}}
    rt = "\n".join(brief_lines(rb))
    case("readable: text that does not read is named with the colour to use, an accent checked at 3; the brief follows "
         "where the logo goes", [r["ok"] for r in readable(rb)] == [False, True]
         and "#1a1a1a text on #0e0e10 1.1:1 does NOT read - on #0e0e10 use #ffffff for text" in rt
         and "no logo in the video" in rt
         and product_card_values(rb, {"name": "X"})["ink"] == "#ffffff")
    # 5c (2026-10-26): the signature end card
    eb = {"name": "RIFT", "site": {"url": "https://riftshoots.com/"}, "end_card": {"style": "title", "line": "Book your shoot"},
          "identity": {"colours": [{"hex": "#1d1d20", "role": "background"}, {"hex": "#ff6600", "role": "accent"}],
                       "fonts": {"heading": "No Such Font"}}}
    e = end_card(eb)
    case("end_card: the picked template filled from the brand - its colours, the sign-off, the website as the button; "
         "a font the template does not offer left out; none picked = None",
         e and e["template"] == "title-card" and e["values"]["main"] == "Book your shoot"
         and e["values"]["button"] == "riftshoots.com" and e["values"]["bg"] == "#1d1d20" and e["values"]["accent"] == "#ff6600"
         and "font" not in e["values"] and end_card({**eb, "end_card": {"style": ""}}) is None
         and clean({"end_card": {"style": "fancy", "line": "x" * 99, "sound": "loud"}})["end_card"]
         == {"style": "", "line": "x" * 60, "sound": ""}
         and e["sound"] == "" and end_card({**eb, "end_card": {**eb["end_card"], "sound": "logo"}})["sound"] == ""
         and clean({"identity": {"sound_logo": "C:/x/sound_logo.wav"}})["identity"]["sound_logo"] == ""
         and "sonic logo for RIFT" in sound_logo_words(eb)
         and "Their signature end card" in "\n".join(brief_lines(eb)))
    pf = clean({"catalogue": [{"id": "p99999", "name": "Music video", "benefit": "Shot like a film in one day",
                               "claims": [{"text": "Delivered in 7 days", "proof": "every 2026 order"}, {"text": ""}, "x"],
                               "never": ["the best in Spain", "the best in Spain", ""],
                               "media": ["C:/x.png", "knowledge/local/brand/products/p1_m1.png",      # another's / none
                                         "knowledge/local/brand/products/p99999_m1.png"]}]})
    p1 = pf["catalogue"][0]
    case("5b: a product's benefit, claims with proof (empty ones out), never-claims de-duplicated, media only its own "
         "files; the brief says only these", p1["claims"] == [{"text": "Delivered in 7 days", "proof": "every 2026 order"}]
         and p1["never"] == ["the best in Spain"] and p1["media"] == []
         and "claims you may make: \"Delivered in 7 days\" (proof: every 2026 order) - NEVER claim: \"the best in Spain\""
         in product_facts(p1) and "Say only what a product's facts say" in "\n".join(brief_lines(pf)))
    wt = "\n".join(brief_lines({"worked": {"hooks": [{"text": "Stop scrolling.", "from": "script-901"}], "ctas": [],
                                           "titles": [{"text": "I Filmed It at 4AM", "from": "title-901"}]}}, "words"))
    case("3j: what worked (their own ratings) in the brief - hooks and titles with where they came from, no empty kind",
         "hooks \"Stop scrolling.\" (script-901); titles \"I Filmed It at 4AM\" (title-901)" in wt and "endings" not in wt)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
