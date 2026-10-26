"""What the user asks of an edit - the Editor's New edit pop-up (2026-10-22, the user: "the edit a video is our most
powerful tool ... give Claude the most options and customability"). Its steps, each optional but the clips: 1 clips,
2 text (what it is about, words on screen, a script or brief from the prompt library), 3 references (up to 3 analysed
videos), 4 style (where it was filmed, the type, the rhythm, the mood, captions, ready-made styles, the user's words,
a colour palette for the graphics), 5 sound (the music, how many sound effects and which kinds, notes), 6 final
(length, format, a DaVinci Resolve project).

    options()            the choices New edit offers (GET /api/edit/options) - English labels, the page translates
                         them by key (ui\\i18n\\parts\\es.server-labels.json)
    clean(body, folder)  the page's answer checked -> the request (build\\edit_request.json, "v": 2); a request of
                         the old dialog (0.4 - 0.5.1: "how", "like", "presets", "want", "prompt"...) still passes
    brief(req, facts)    the request in words, one section per step with what to do with it -> build\\edit_brief.md,
                         what /recreate-video request <p> follows
    draft_args(req)      the quick draft's arguments (tools\\draft_edit.py)

Nothing is written here (motionlab.app.data saves); the clips and songs are only looked at.
"""
from __future__ import annotations

import re
from pathlib import Path

from motionlab import brand as BR
from motionlab import i18n as I18N
from motionlab import style as ST
from motionlab.styles import CATEGORIES
from motionlab.util import ANALYSIS, LAB

AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg"}
SONGS = LAB / "refs" / "audio"                     # downloaded songs (Analyser > download as MP3)
PROMPT_ID = r"(shot|image|hook|script|brief|title)-\d{3,}"
TALK_ID = r"(script|hook)-\d{3,}"                  # a talking video: the user films the script
SOUND = ("auto", "music", "clips", "talk")
MIN_PER_S = 1.0                                    # New edit's estimate: about a minute of Claude per second of video

# 4. Style - every table: id -> {"label", "help"}; the numbers after them are for Claude and the quick draft
WHERE = {
    "home": {"label": "Home / indoors", "help": "mixed window and lamp light"},
    "city": {"label": "City / street", "help": "street, shops, traffic"},
    "nature": {"label": "Nature / outdoors", "help": "daylight, landscapes"},
    "studio": {"label": "Studio / set", "help": "controlled light, a backdrop"},
    "event": {"label": "Event / night out", "help": "concert, party, low light"},
    "travel": {"label": "Travel", "help": "many places, a journey"},
    "screen": {"label": "Screen recording", "help": "an app, a website, a game"},
}
RHYTHM = {
    "calm": {"label": "Calm", "help": "long shots, 4 s or more", "shot_s": 4.5, "preset": "slow_cinematic"},
    "steady": {"label": "Steady", "help": "a cut every 2-3 s", "shot_s": 2.5, "preset": "three_sec"},
    "fast": {"label": "Fast", "help": "a cut about every second", "shot_s": 1.1, "preset": "fast_hook"},
    "frantic": {"label": "Very fast", "help": "a cut on every beat", "shot_s": 0.6, "preset": "beat_montage"},
}
MOODS = {
    "energetic": {"label": "Energetic", "help": ""},
    "cinematic": {"label": "Cinematic", "help": ""},
    "fun": {"label": "Fun", "help": ""},
    "emotional": {"label": "Emotional", "help": ""},
    "premium": {"label": "Clean & premium", "help": ""},
    "raw": {"label": "Raw & real", "help": ""},
    "dark": {"label": "Dark & moody", "help": ""},
    "dreamy": {"label": "Dreamy", "help": ""},
}
MAX_MOODS = 3
CAPTIONS = {
    "words": {"label": "Every word", "help": "word by word, as it is said"},
    "key": {"label": "Key words only", "help": "the words that matter, big"},
    "none": {"label": "No captions", "help": ""},
}
PALETTES = {                                       # ready-made palettes; the first colour = the main accent
    "bold": {"label": "Bold red", "colours": ["#FF2D55", "#FFFFFF", "#111111"]},
    "neon": {"label": "Neon night", "colours": ["#00E5FF", "#FF2BD6", "#0B0B1A"]},
    "sunset": {"label": "Warm sunset", "colours": ["#FF7A00", "#FFC93C", "#2B1B17"]},
    "gold": {"label": "Black & gold", "colours": ["#D4AF37", "#0D0D0D", "#F5F5F5"]},
    "fresh": {"label": "Fresh green", "colours": ["#3ECF8E", "#F5F1E6", "#16301F"]},
    "pastel": {"label": "Soft pastel", "colours": ["#FFD1DC", "#C7CEEA", "#FFFFFF"]},
    "mono": {"label": "Clean mono", "colours": ["#FFFFFF", "#9A9AA3", "#0E0E10"]},
}
MAX_COLOURS = 6

# 5. Sound - how many effects, and which kinds (the cue kinds of motionlab\\sfx.py: tools\\sfx.py kinds)
SFX_AMOUNT = {
    "none": {"label": "None", "help": "no sound effects", "rule": "No sound effects at all - skip sfx.py."},
    "few": {"label": "A few", "help": "only the big moments",
            "rule": "A few: only the big moments (the hook, drops, reveals, the end) - about one every 5-8 s."},
    "some": {"label": "Some", "help": "most cuts and graphics",
             "rule": "Some: on most cuts with movement and on graphics popping in - about one every 2-4 s."},
    "many": {"label": "Many", "help": "on every move",
             "rule": "Many: on every move, every cut with movement and every graphic - dense, like a velocity edit."},
}
SFX_KINDS = {
    "whoosh": {"label": "Whooshes", "help": "transitions, fast moves", "kinds": ["whoosh", "whip", "air"]},
    "impact": {"label": "Impacts", "help": "drops, big reveals", "kinds": ["impact", "thump"]},
    "riser": {"label": "Risers", "help": "build-ups before a cut", "kinds": ["riser"]},
    "ui": {"label": "Clicks & pops", "help": "text, buttons, pop-ins", "kinds": ["click", "pop", "key", "tick", "chime", "shutter"]},
    "glitch": {"label": "Glitches", "help": "glitches, inverted frames", "kinds": ["zap", "buzz", "crackle"]},
    "playful": {"label": "Playful & 8-bit", "help": "games, money, fun", "kinds": ["chip", "chip_hit", "ching", "cork"]},
    "sparkle": {"label": "Sparkle", "help": "glows, light leaks", "kinds": ["shimmer", "flutter", "ghost"]},
}
# 2. Text - product motion (0.6.0, My Brand step 5): a product of My Brand's catalogue shown with the Motion Graphics
# template "product-card" - in passing, as the call to action at the end, or both
PRODUCT_HOW = {
    "passing": "in passing: 2-3 s, background off (see-through, its words on a card of their own), over a shot where "
               "the product fits - in the lower part of the frame, never over a face",
    "end": "as the call to action at the end: background on, the last 3-4 s, after the last shot (the price and the "
           "button with the website stay on screen to the end)",
    "both": "both: once in passing (2-3 s, background off, over a shot where it fits) and again as the call to action "
            "at the end (background on, the last 3-4 s)",
}
MAX_PRODUCTS = 2
MAX_SOUNDS = 40                                     # 0.6.0: the library sounds one edit may be given
FORMAT_WORDS = {"vertical": "vertical 9:16 (1080x1920) - TikTok, Reels, Shorts",
                "horizontal": "horizontal 16:9 (1920x1080) - YouTube", "square": "square 1:1 (1080x1080) - a feed"}


def _rows(table: dict, *keys: str) -> list[dict]:
    return [{"id": k, **{x: v[x] for x in ("label", "help", *keys) if x in v}} for k, v in table.items()]


def options() -> dict:
    """New edit's choices (labels in English: the page translates them by key)."""
    return {"where": _rows(WHERE), "types": [{"id": k, "label": v, "help": ""} for k, v in CATEGORIES.items()],
            "rhythm": _rows(RHYTHM), "moods": _rows(MOODS), "max_moods": MAX_MOODS, "captions": _rows(CAPTIONS),
            "palettes": _rows(PALETTES, "colours"), "max_colours": MAX_COLOURS, "sfx_amount": _rows(SFX_AMOUNT),
            "sfx_kinds": _rows(SFX_KINDS), "presets": ST.presets_info(), "max_refs": ST.MAX_REFS,
            "formats": sorted(ST.SIZES), "min_per_s": MIN_PER_S, **_music_options()}


def _music_options() -> dict:
    """0.6.0 step 10: the music library's songs (downloaded + added, the hidden ones left out, ★ first) with their
    measures, and its ambience beds."""
    from . import music as MU
    keep = ("rel", "title", "artist", "from", "fav", "len_s", "bpm", "energy", "tone", "kind")
    rows = [x for x in MU.state()["tracks"] if not x["off"]]
    return {"songs": [{"name": Path(x["rel"]).name, **{k: x[k] for k in keep if k in x}} for x in rows
                      if x["type"] == "song"],
            "beds": [{k: x[k] for k in keep if k in x} for x in rows if x["type"] == "bed"]}


# ------------------------------------------------------------------ the check
def _text(v, n: int, lines: bool = False) -> str:
    """Spaces folded (line breaks kept when lines), at most n characters."""
    s = str(v or "")
    s = "\n".join(" ".join(x.split()) for x in s.splitlines() if x.strip()) if lines else " ".join(s.split())
    return s[:n]


def _one(table: dict, v, field: str) -> str | None:
    v = str(v or "")
    if v and v not in table:
        raise ValueError(I18N.t("{field}: one of {choices}", field=field, choices=", ".join(table)))
    return v or None


def _some(table: dict, vs, field: str, most: int | None = None) -> list[str]:
    out = list(dict.fromkeys(str(x) for x in (vs or []) if str(x)))
    for x in out:
        _one(table, x, field)
    if most is not None and len(out) > most:
        raise ValueError(I18N.t("{field}: at most {n}", field=field, n=most))
    return out


def _music(v, folder: Path) -> str | None:
    """A song in the video's folder (its file name) or a downloaded one (refs/audio/<file>, lab-relative)."""
    v = str(v or "").replace("\\", "/")
    if not v or v == "none":
        return v or None
    if "/" not in v:
        ok = (folder / v).is_file() and Path(v).suffix.lower() in AUDIO_EXT
    else:
        from . import music as MU                   # a downloaded song, or one added to the music library (0.6.0)
        p = (LAB / v).resolve()
        ok = p.is_file() and p.suffix.lower() in AUDIO_EXT and (
            p.parent == SONGS.resolve() or (MU.ROOT.resolve() in p.parents and "ambience" not in
                                            [x.lower() for x in p.relative_to(MU.ROOT.resolve()).parts]))
    if not ok:
        raise ValueError(I18N.t("{file}: not a song in the video's folder or in refs\\audio", file=v))
    return v


def _bed(v) -> str | None:
    """0.6.0 step 10: an ambience bed of the music library (its lab-relative path), or None."""
    from . import music as MU
    v = str(v or "").replace("\\", "/")
    if not v:
        return None
    if not any(x["rel"] == v and x["type"] == "bed" for x in MU.state()["tracks"]):
        raise ValueError(I18N.t("{file}: not an ambience bed of the music library", file=v[-80:]))
    return v


def how_of(req: dict) -> str:
    """What the edit is mainly made from (made_from.json, the quick draft): an exact copy > videos' style > a
    prompt > the user's words (presets, their words, the style questions - or nothing: Claude starts blind)."""
    return "copy" if req.get("exact") else "style" if req.get("like") else "prompt" if req.get("prompt") else "words"


def made_from(req: dict) -> list[tuple[str, str]]:
    """The made_from.json entries (kind, id) of a request: its main source, + the prompt when it is used beside
    videos' style (so the prompt's card says "Used in"). "words" names the labels picked (the page translates them
    by key), else the user's words, else "Claude's choice"."""
    how, st = req["how"], req.get("style") or {}
    if how == "copy":
        out = [("reference", req["like"][0])]
    elif how == "style":
        out = [("style", ", ".join(req["like"]))]
    elif how == "prompt":
        out = [("prompt", req["prompt"])]
    else:
        names = [ST.PRESETS[x]["label"] for x in req.get("presets") or []] + (
            [RHYTHM[st["rhythm"]]["label"]] if st.get("rhythm") else []) + [MOODS[m]["label"] for m in st.get("moods") or []]
        out = [("words", ", ".join(names) or req.get("want", "")[:120] or req.get("about", "")[:120] or "Claude's choice")]
    if req.get("prompt") and how != "prompt":
        out.append(("prompt", req["prompt"]))
    return out


def clean(body: dict, folder: Path) -> dict:
    """The page's answer (or the old dialog's) checked -> the request, without its date (the caller stamps it)."""
    like = [" ".join(str(x).split()) for x in (body.get("like") or []) if str(x).strip()]
    if len(like) > ST.MAX_REFS:
        raise ValueError(I18N.t("at most {n} videos for one edit", n=ST.MAX_REFS))
    for x in like:
        if x.startswith("-") or len(x) > 160 or ST.find(x) is None:
            raise ValueError(I18N.t("no analysed video called {name}", name=repr(x)))
    exact = bool(body.get("exact")) or body.get("how") == "copy"
    if exact and (len(like) != 1 or not re.fullmatch(r"[\w.\- \[\]()&'+,]+", like[0]) or ".." in like[0]
                  or not (ANALYSIS / like[0] / "events.json").exists()):
        raise ValueError(I18N.t("an exact copy needs one video analysed on this PC"))
    prompt = str(body.get("prompt") or "")
    if prompt and not re.fullmatch(PROMPT_ID, prompt):
        raise ValueError(I18N.t("not a prompt id: {id}", id=repr(prompt)))
    presets = [str(x) for x in (body.get("presets") or [])]
    bad = [x for x in presets if x not in ST.PRESETS]
    if bad:
        raise ValueError(I18N.t("unknown preset {id}", id=repr(bad[0])))
    sty = body.get("style") if isinstance(body.get("style"), dict) else {}
    palette = [str(c).upper() for c in (sty.get("palette") or []) if str(c).strip()]
    if len(palette) > MAX_COLOURS or any(not re.fullmatch(r"#[0-9A-F]{6}", c) for c in palette):
        raise ValueError(I18N.t("palette: up to {n} colours like #FF2D55", n=MAX_COLOURS))
    sfx = body.get("sfx") if isinstance(body.get("sfx"), dict) else {}
    length = body.get("length_s")
    length = float(length) if length not in (None, "") else None
    if length is not None and not 3 <= length <= 900:
        raise ValueError(I18N.t("length: 3 to 900 seconds"))
    fmt = body.get("format") or None
    if fmt is not None and fmt not in ST.SIZES:
        raise ValueError(I18N.t("format: one of {choices}", choices=", ".join(ST.SIZES)))
    sound = str(body.get("sound") or "auto")
    if sound not in SOUND:
        raise ValueError(I18N.t("sound: one of {choices}", choices=", ".join(SOUND)))
    ons = body.get("on_screen")                     # one line each (a list, or the text box as it is)
    ons = "\n".join(map(str, ons)) if isinstance(ons, list) else ons
    photos = {}                                     # 2026-10-24: a photo's own length / zoom / fit (1. Clips)
    for name, o in (body.get("photos") or {}).items() if isinstance(body.get("photos"), dict) else []:
        if not isinstance(o, dict) or not (folder / str(name)).is_file() or Path(str(name)).name != name:
            continue
        sec = o.get("seconds")
        sec = float(sec) if sec not in (None, "") else None
        if sec is not None and not 0.5 <= sec <= 60:
            raise ValueError(I18N.t("a photo shows for 0.5 to 60 seconds"))
        x = {k: v for k, v in (("seconds", sec), ("zoom", False if o.get("zoom") is False else None),
                                 ("fit", "contain" if o.get("fit") == "contain" else None)) if v is not None}
        if x:
            photos[str(name)] = x
    products = []                                   # 0.6.0 product motion: My Brand's products, switched on for videos
    if isinstance(body.get("products"), list) and body["products"]:
        cat = {p["id"]: p for p in BR.load().get("catalogue") or [] if p.get("use") is not False}
        for x in list(body.get("products"))[:MAX_PRODUCTS]:
            pid = str((x or {}).get("id") or "")
            if pid not in cat:
                raise ValueError(I18N.t("a product that is not in My Brand's catalogue for videos: {id}", id=pid[:20]))
            if pid not in [p["id"] for p in products]:
                p = cat[pid]
                products.append({"id": pid, "how": x.get("how") if x.get("how") in PRODUCT_HOW else "end", "name": p["name"],
                                 "what": p.get("what", ""), "price": p.get("price", ""), "url": p.get("url", ""),
                                 "image": p.get("image", ""),
                                 **{k: p[k] for k in ("benefit", "claims", "never", "media") if p.get(k)}})   # 5b
    req = {"v": 2, "like": like, "exact": exact, "prompt": prompt or None, "products": products,
           "about": _text(body.get("about"), 2000, lines=True),
           "on_screen": [x[:120] for x in _text(ons, 2000, lines=True).splitlines()[:12]],
           "presets": presets, "want": _text(body.get("want"), 1500),
           "style": {"where": _one(WHERE, sty.get("where"), "where"), "type": _one(CATEGORIES, sty.get("type"), "type"),
                     "rhythm": _one(RHYTHM, sty.get("rhythm"), "rhythm"),
                     "moods": _some(MOODS, sty.get("moods"), "moods", MAX_MOODS),
                     "captions": _one(CAPTIONS, sty.get("captions"), "captions"), "palette": palette},
           "sfx": {"amount": _one(SFX_AMOUNT, sfx.get("amount"), "sfx"), "kinds": _some(SFX_KINDS, sfx.get("kinds"), "kinds"),
                   "notes": _text(sfx.get("notes"), 600), "sounds": _sounds(sfx.get("sounds"))},
           "length_s": length, "format": fmt, "music": _music(body.get("music"), folder), "sound": sound,
           "ambience": _bed(body.get("ambience")),
           "resolve": bool(body.get("resolve")), "photos": photos,
           "brand": BR.snapshot() if body.get("brand") else None}      # 0.6.0: For my brand - My Brand as it is now
    req["how"] = how_of(req)
    return req


def _sounds(files) -> list[str]:
    """0.6.0 New edit's *Choose the sounds*: this PC's library sounds the user ticked (in use, by their file)."""
    if not files:
        return []
    from . import sfx as SFX
    lib = SFX.Library.load()
    ok = [str(f) for f in list(files)[:MAX_SOUNDS] if lib is not None and lib.entry(str(f)) not in (None, SFX.Library.SYNTH)]
    if len(ok) != len(list(files)[:MAX_SOUNDS]):
        raise ValueError(I18N.t("a sound that is not in this PC's library"))
    return ok


# ------------------------------------------------------------------ the brief Claude follows
def _quote(s: str) -> list[str]:
    return [f"  > {x}" for x in s.splitlines()]


def estimate_min(req: dict) -> float | None:
    """The page's estimate of Claude's time: about MIN_PER_S minutes per second of the video (a length picked)."""
    return round(req["length_s"] * MIN_PER_S) if req.get("length_s") else None


def brief(req: dict, f: dict) -> str:
    """The request in words for Claude (build\\edit_brief.md): one section per step of New edit, each line what the
    user picked and what to do with it; what they left on automatic is said to be Claude's call. f = what the app
    knew when it saved: project, label, clips (count), songs (names), refs {analysis: readable name},
    prompt {title, kind} (or None)."""
    st, sx = req.get("style") or {}, req.get("sfx") or {}
    p = f["project"]
    L = [f"# Edit request: {f.get('label') or p}", "",
         f"Saved by the app (Editor > New edit) on {req.get('date', '')} for `projects\\{p}`; the same data is "
         "`build\\edit_request.json`. Follow it step by step with /recreate-video - *cheapest check first*, the user "
         "approves each step. Anything the user left on automatic is your call: decide it from the references, "
         "Claude's memory and their ratings, and say what you chose.", ""]
    if req.get("brand"):                             # 0.6.0: For my brand, first - it shapes every step below
        L += ["## For my brand", *BR.brief_lines(req["brand"], "video"), ""]
    L += ["## 1. Clips",
          f"- {f.get('clips', 0)} clip(s) in `projects\\{p}` - read-only; everything you make goes into `build\\`."]
    if f.get("photos"):
        from motionlab import photos as PH
        own = req.get("photos") or {}
        L.append(f"- {len(f['photos'])} photo(s) among them - still shots, not videos: place them in the story "
                 f"({PH.SECONDS:g} s each with a slow zoom unless set here; silent; `build\\brief.md` *The photos*).")
        L += [f"  - {n}: " + ", ".join(x for x in (f"{o['seconds']:g} s" if o.get("seconds") else "",
                                                   "no zoom" if o.get("zoom") is False else "",
                                                   "the whole photo, over a blurred copy" if o.get("fit") == "contain"
                                                   else "") if x)
              for n, o in own.items() if n in f["photos"]]
    if f.get("songs"):
        L.append(f"- Songs in the folder: {', '.join(f['songs'])}.")
    # 2. Text, 3. References
    L += ["", "## 2. Text"]
    talk = bool(re.fullmatch(TALK_ID, req.get("prompt") or ""))
    if req.get("about"):
        L += ["- **What it is about** (the user's words - the story, who it is for, the feel):", *_quote(req["about"])]
    if req.get("on_screen"):
        L += ["- **Words on screen, exactly as written** (titles, captions or graphics - keep the spelling, the case "
              "and the order; place each where it fits the story):", *[f"  {i}. {x}" for i, x in
                                                                     enumerate(req["on_screen"], 1)]]
    if req.get("prompt"):
        pr = f.get("prompt") or {}
        L.append(f"- **From the prompt library**: `{req['prompt']}`" + (f" - {pr['title']}" if pr.get("title") else "")
                 + f" (read it: `prompts(id=\"{req['prompt']}\")`). " + (
                     "A talking script: the user filmed it - follow the script (the skill's *script / hook*)."
                     if talk else "Follow it part by part; ask what it leaves open in one message before building."))
    if not (req.get("about") or req.get("on_screen") or req.get("prompt")):
        L.append("- Nothing written: start from the clips' storyboards.")
    if req.get("products"):                          # 0.6.0 product motion
        import json as _json
        b = req.get("brand") or BR.load()
        logo = BR.logo_for(b, BR.product_card_values(b, {}).get("paper"))   # the version that reads on the card
        L.append("- **Products to show** (product motion - My Brand's catalogue; each price exactly as written). Build each "
                 "from the Motion Graphics template `product-card`: `tools\\overlay.py new build\\overlays\\product_<id> "
                 "--from product-card --values <the JSON below>` (pass it as one argument from Python, not through a "
                 "shell), then `overlay.py fit` to the edit's size; copy the product's picture into the graphic's "
                 "`assets\\media\\` and set `product_media` to `assets/media/<its file>`" + (
                     f", the logo (`{logo}`) the same way into `logo_media`" if logo else "") + ":")
        for p in req["products"]:
            L.append(f"  - **{p['name']}**" + (f" - {p['price']}" if p.get("price") else "") + f" - {PRODUCT_HOW[p['how']]}"
                     + (f"; its picture `{p['image']}`" if p.get("image") else "; no picture: the card's placeholder, or a "
                                                                                 "frame of the clips that shows it")
                     + f"; settings {_json.dumps(BR.product_card_values(b, p), ensure_ascii=False)}"
                     + BR.product_facts(p).replace(" - ", "; ", 1))      # 5b: say only what its facts say
    L += ["", "## 3. References"]
    if req.get("like"):
        refs = f.get("refs") or {}
        L.append("- **References** - " + ("an exact 1:1 copy: the same song, the same cuts and effects frame by frame "
                                           "with the user's clips (the skill's copy.md):" if req.get("exact") else
                                           "their style, mixed: `tools\\style.py` with them (+ the presets and words "
                                           "of 4) - their rhythm, effects and captions, never their content "
                                           "(the skill's by_feel.md):"))
        L += [f"  - `{k}`" + (f" - {refs[k]}" if refs.get(k) and refs[k] != k else "") for k in req["like"]]
    elif ((req.get("brand") or {}).get("look") or {}).get("like"):
        L.append("- None picked here, but **For my brand** is ticked: the brand's editing look is the reference - "
                 + ", ".join(f"`{x}`" for x in req["brand"]["look"]["like"]) + " - their style, mixed (`tools\\style.py` "
                 "with them + 4. Style; the skill's by_feel.md).")
    else:
        L.append("- None: the style comes from 4. Style (nothing there either = `tools\\style.py closest \"<their "
                 "words>\"` first, the skill's by_feel.md step 0).")
    # 4. Style
    L += ["", "## 4. Style"]
    rows = []
    if st.get("where"):
        rows.append(f"- Filmed: {WHERE[st['where']]['label']} ({WHERE[st['where']]['help']}).")
    if st.get("type"):
        rows.append(f"- Type of video: {CATEGORIES[st['type']]}.")
    if st.get("rhythm"):
        r = RHYTHM[st["rhythm"]]
        rows.append(f"- Rhythm: {r['label']} ({r['help']}) - aim for a typical (median) shot of about {r['shot_s']:g} s.")
    if st.get("moods"):
        rows.append(f"- Mood: {', '.join(MOODS[m]['label'] for m in st['moods'])}.")
    if st.get("captions"):
        rows.append(f"- Captions: {CAPTIONS[st['captions']]['label']}"
                    + (f" ({CAPTIONS[st['captions']]['help']})" if CAPTIONS[st['captions']]['help'] else "")
                    + (" - `tools\\speech.py` + `overlay.py captions`." if st["captions"] != "none" else "."))
    for k in req.get("presets") or []:
        rows.append(f"- Ready-made style *{ST.PRESETS[k]['label']}*: {ST.PRESETS[k]['words']}")
    if req.get("want"):
        rows += ["- **In the user's words**:", *_quote(req["want"])]
    if st.get("palette"):
        rows.append(f"- **Colour palette**: {', '.join(st['palette'])} - the colours of every title, caption and "
                    "graphic (the overlays' colour settings; the first = the main accent). Not a grade of the footage.")
    L += rows or ["- Nothing picked: the references' style, else the closest analysed video (`style.py closest`)."]
    # 5. Sound
    L += ["", "## 5. Sound"]
    snd, music = req.get("sound") or "auto", req.get("music")
    L.append("- Music: " + (f"the song `{music}`" + (" (a download in refs\\audio)" if "/" in music else " (in the "
                                                                                                       "folder)")
                            if music and music != "none" else
                            "the clips' own sound, shot by shot" if snd == "clips" or music == "none" else
                            "talking - keep what is said in order, cut the pauses" if snd == "talk" else
                            "automatic - the song in the folder if there is one, else the clips' own sound") + ".")
    if req.get("ambience"):
        L.append(f"- **Ambience under the voice** (the user's pick, the music library): `{req['ambience']}` - put "
                 f"`\"bed\": {{\"file\": \"{req['ambience']}\"}}` in the plan's `\"sfx\"`; `sfx.py plan` / build.py loop "
                 "it under the voice, 26 dB under the words (`\"db\"` changes that), faded in and out.")
    L.append("- Sound effects: " + (SFX_AMOUNT[sx["amount"]]["rule"] if sx.get("amount") else
                                    "automatic - as the references' sound answer says (`verdicts(...)` \"sound\"), else "
                                    "Claude's memory ratings (rated bad once = add them)."))
    if sx.get("kinds") and sx.get("amount") != "none":
        kinds = [k for g in sx["kinds"] for k in SFX_KINDS[g]["kinds"]]
        L.append(f"- Kinds the user wants ({', '.join(SFX_KINDS[g]['label'] for g in sx['kinds'])}): the cue kinds "
                 f"{', '.join(kinds)} - set them as the plan's own `cues`; other kinds only where none of these fits.")
    if sx.get("sounds") and sx.get("amount") != "none":
        L.append("- **The sounds the user picked** (this PC's library): a kind with sounds here uses only those - put "
                 "them in the plan's `\"sfx\": {\"sounds\": [...]}` (sfx.py plan and build.py keep it): "
                 + ", ".join(f"`{f}`" for f in sx["sounds"]) + ".")
    if sx.get("notes"):
        L += ["- **Notes on sound**:", *_quote(sx["notes"])]
    if sx.get("amount") != "none":
        L.append("- Make them with `tools\\sfx.py plan` (each levelled against the music) and check them with "
                 "`precheck.py --sfx` before the final.")
    # 6. Final
    L += ["", "## 6. Final",
          "- Length: " + (f"{req['length_s']:g} s." if req.get("length_s") else
                          "automatic - the reference's for a 1:1 copy, else what the song and the story need."),
          "- Format: " + (FORMAT_WORDS.get(req["format"], req["format"]) + "." if req.get("format") else
                          "automatic - the footage's own shape (a 1:1 copy: the reference's)."),
          "- DaVinci Resolve: " + ("yes - build it (the skill's render.md, option 2) once the user approves the lab "
                                   "render." if req.get("resolve") else "no - the lab render only.")]
    m = estimate_min(req)
    if m:
        L.append(f"- The app told the user this could take about {m:g} min of Claude (about {MIN_PER_S:g} min per "
                 "second of video): keep to it - the cheapest check first, one final render.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ the quick draft
def draft_args(req: dict) -> list[str]:
    """draft_edit.py's arguments for a saved request (the quick draft job). A script or hook = a talking video: the
    talking preset, its sound kept and the pauses cut. No ready-made style picked: the rhythm's."""
    talk = bool(re.fullmatch(TALK_ID, str(req.get("prompt") or "")))
    presets = list(req.get("presets") or [])
    rhythm = (req.get("style") or {}).get("rhythm")
    if not presets and rhythm in RHYTHM and not talk:
        presets = [RHYTHM[rhythm]["preset"]]
    # For my brand and no references picked: the brand's editing look (0.6.0, My Brand)
    like = req.get("like") or [x for x in ((req.get("brand") or {}).get("look") or {}).get("like") or []
                                if ST.find(x) is not None]
    if req.get("exact") or req.get("how") == "copy" or not (like or presets or req.get("want") or talk):
        raise ValueError(I18N.t("a quick draft is made from videos' style, your words or a talking script "
                                "(an exact copy or another prompt: Claude)"))
    out: list[str] = ["--preset", "talking"] if talk else []
    for x in like:
        out += ["--like", x]
    for x in presets:
        out += ["--preset", x]
    if req.get("want"):
        out += ["--want", req["want"]]
    if req.get("length_s"):
        out += ["--length", f"{float(req['length_s']):g}"]
    if req.get("format"):
        out += ["--format", req["format"]]
    music = req.get("music")
    if music:
        out += ["--music", str(LAB / music) if "/" in music else music]
    sound = req.get("sound") or "auto"
    if talk and sound == "auto":
        sound = "talk"
    if sound != "auto":
        out += ["--sound", sound]
    sx = req.get("sfx") or {}                       # 0.5.4: the draft's own sound effects (Auto = few / some)
    if sx.get("amount") != "none":
        out += ["--sfx", sx.get("amount") or "auto"]
        kinds = [k for g in sx.get("kinds") or [] if g in SFX_KINDS for k in SFX_KINDS[g]["kinds"]]
        if kinds:
            out += ["--sfx-kinds", ",".join(kinds)]
        if sx.get("sounds"):
            out += ["--sfx-sounds", ",".join(sx["sounds"])]
    if req.get("ambience"):
        out += ["--ambience", str(LAB / req["ambience"])]
    return out
