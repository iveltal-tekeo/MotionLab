"""Import from your website (0.6.0, My Brand step 2; the user, 2026-10-25: "an option besides the 'your website' with a
download icon that 'imports data from your website' so if its a shop website it will pull the catalog data,
descriptions, logos... a good foundation regarding your brand instead of filling up everything by hand").

    read(url, log)      the user's own site -> what My Brand can hold, written to knowledge\\local\\brand\\import\\
                        (found.json + the pictures); nothing goes into My Brand here - the page shows what was found
                        and the user ticks what is right (brand.take_import)
    selfcheck()         the parsers on made-up pages (no network)

What it looks for: the name and description (og:site_name, JSON-LD Organization, <title>, the meta description); the
colours (theme-color, then the CSS's most used ones - brand / primary / accent custom properties count more); the
fonts (Google Fonts links, @font-face, font-family; `library` = the lab's font folder has it); logos (JSON-LD logo,
<img> named logo, apple-touch-icon / icons, og:image as the share picture); the brand's pages (YouTube, TikTok,
Instagram, X, LinkedIn, Facebook, Threads, Twitch; placeholders like /HANDLE/ left out); products (a Shopify shop's
/products.json, WooCommerce's Store API, JSON-LD Product / Service / Offer, og product prices) with their picture.
Rules: the site's own host (www. or not) for pages, robots.txt obeyed, at most MAX_PAGES pages - the home page, then
the links that look like a shop, prices, services or about; https; no login, no cookies; pictures may come from a
CDN, checked by their first bytes, at most 5 MB.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

from .util import LAB

IMPORT = LAB / "knowledge" / "local" / "brand" / "import"
MAX_PAGES = 8                        # the home page + 7 more
MAX_CSS = 4                          # the site's own stylesheets read for colours and fonts
MAX_BYTES = 2_000_000                # a page / a stylesheet / a shop's JSON
MAX_PIC = 5_000_000
MAX_PRODUCTS = 60
TIMEOUT = 15
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MotionLab-brand-import"
ROBOTS_UA = "MotionLab"
LIKELY = re.compile(r"shop|store|tienda|product|catalog|collection|pricing|price|precio|tarifa|servic|package|paquete|"
                    r"plan|about|nosotros|sobre|quienes|portfolio|work|trabajo", re.I)
SKIP_EXT = re.compile(r"\.(jpe?g|png|gif|webp|svg|ico|pdf|zip|mp4|mov|mp3|css|js|xml|json|txt)(\?|$)", re.I)
SOCIAL = {                           # platform -> a profile address (the post / share / intent links do not match)
    "youtube": r"(?:www\.|m\.)?youtube\.com/(?:@[\w.-]+|c/[\w.-]+|channel/[\w-]+|user/[\w.-]+)",
    "tiktok": r"(?:www\.)?tiktok\.com/@[\w.-]+",
    "instagram": r"(?:www\.)?instagram\.com/[\w.]+",
    "x": r"(?:www\.)?(?:x|twitter)\.com/\w+",
    "linkedin": r"(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in)/[\w.-]+",
    "facebook": r"(?:www\.|m\.)?facebook\.com/[\w.-]+",
    "threads": r"(?:www\.)?threads\.(?:net|com)/@[\w.]+",
    "twitch": r"(?:www\.)?twitch\.tv/\w+",
}
NOT_A_HANDLE = {"handle", "username", "user", "yourname", "yourhandle", "your_handle", "your-handle", "example", "account",
                "profile", "intent", "share", "sharer", "sharer.php", "home", "explore", "p", "reel", "reels", "tv",
                "watch", "hashtag", "search", "login", "signup", "dialog", "plugins", "tr", "about", "legal", "privacy"}
PLACEHOLDERS = {"handle", "username", "user", "yourname", "yourhandle", "your_handle", "your-handle", "example"}
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-sans-serif", "ui-serif",
                 "ui-monospace", "ui-rounded", "-apple-system", "blinkmacsystemfont", "segoe ui", "arial", "helvetica",
                 "helvetica neue", "inherit", "initial", "unset", "emoji", "math", "roboto", "apple color emoji",
                 "segoe ui emoji", "segoe ui symbol", "noto color emoji", "times new roman", "courier new", "georgia",
                 "verdana", "tahoma", "sans", "revert"}
CURRENCY = {"EUR": ("", " €"), "USD": ("$", ""), "GBP": ("£", ""), "MXN": ("$", " MXN"), "ARS": ("$", " ARS"),
            "COP": ("$", " COP"), "CLP": ("$", " CLP"), "CAD": ("$", " CAD"), "AUD": ("$", " AUD")}


# ------------------------------------------------------------------------------------------------- one page
class _Page(HTMLParser):
    """What a page holds for My Brand: meta tags, links, pictures, anchors, JSON-LD, <style>, inline styles, <title>."""

    BLOCKS = ("h1", "h2", "h3", "h4", "p", "li", "blockquote", "dd", "figcaption")
    SKIP = ("nav", "footer", "aside", "form", "script", "style", "noscript", "svg", "button", "select", "template")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.links, self.imgs, self.hrefs = {}, [], [], []
        self.ld, self.styles, self.inline, self.title = [], [], [], ""
        self._in, self._buf = None, []
        self.blocks, self._blk, self._txt, self._skip = [], None, [], 0       # the readable text: (tag, words)
        self.loose = []                     # longer text outside those tags (sites built of <div>s: Framer, Webflow...)

    def _flush(self):
        if self._blk:
            s = " ".join("".join(self._txt).split())
            if s:
                self.blocks.append((self._blk, s))
        self._blk, self._txt = None, []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCKS:
            self._flush()
            self._blk = tag
        elif tag == "br" and self._blk:
            self._txt.append(" ")
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            k = (a.get("property") or a.get("name") or a.get("itemprop") or "").lower()
            if k and "content" in a:
                self.meta.setdefault(k, a["content"])
        elif tag == "link":
            self.links.append(a)
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        elif tag == "script" and "ld+json" in a.get("type", "").lower():
            self._in, self._buf = "ld", []
        elif tag in ("style", "title"):
            self._in, self._buf = tag, []
        if a.get("style"):
            self.inline.append(a["style"])

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in self.BLOCKS and self._blk == tag:
            self._flush()
        if self._in and tag in ("script", "style", "title"):
            txt = "".join(self._buf)
            if self._in == "ld":
                self.ld.append(txt)
            elif self._in == "style":
                self.styles.append(txt)
            elif self._in == "title" and not self.title:
                self.title = " ".join(txt.split())
            self._in = None

    def handle_data(self, d):
        if self._in:
            self._buf.append(d)
        elif self._blk and not self._skip:
            self._txt.append(d)
        elif not self._skip:
            s = " ".join(d.split())
            if len(s) >= 40:
                self.loose.append(("p", s))


def parse(html: str) -> _Page:
    p = _Page()
    try:
        p.feed(html)
        p.close()
        p._flush()
    except Exception:                                   # a broken page: what was read so far
        pass
    return p


def site_text(parsed: list[tuple[str, "_Page"]], limit: int = 12000) -> tuple[str, int]:
    """What the pages say, as Markdown (a page = its title, then its headings, paragraphs and list items), for Claude
    to read for facts: blocks seen on every page (a footer, a slogan), cookie notices and scraps under 25 characters
    (headings excepted) left out; at most `limit` characters. -> (markdown, how many blocks kept)."""
    blocks = {url: (p.blocks if len(p.blocks) >= 3 else p.blocks + p.loose) for url, p in parsed}   # few real ones: the loose too
    seen: dict[str, int] = {}
    for url, _ in parsed:
        for _, s in dict.fromkeys(blocks[url]):
            seen[s] = seen.get(s, 0) + 1
    out, n, size = [], 0, 0
    for url, p in parsed:
        rows = []
        for tag, s in dict.fromkeys(blocks[url]):
            head = tag in ("h1", "h2", "h3", "h4")
            if (len(parsed) > 1 and seen[s] == len(parsed)) or re.search(r"(?i)\bcookies?\b", s) \
                    or (not head and len(s) < 25) or len(s) > 2000:
                continue
            rows.append(("### " if head else "- " if tag == "li" else "") + s)
        if not rows:
            continue
        block = f"## {p.title or urllib.parse.urlsplit(url).path or '/'}\n" + "\n".join(rows) + "\n"
        if size + len(block) > limit:
            break
        out.append(block)
        size += len(block)
        n += len(rows)
    return "\n".join(out), n


def _text(v, n: int) -> str:
    """HTML or text -> plain words, at most n characters (cut at a word)."""
    s = re.sub(r"<[^>]+>", " ", str(v or ""))
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = " ".join(s.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'").split())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def _host(u: str) -> str:
    h = urllib.parse.urlsplit(u).hostname or ""
    return h[4:] if h.startswith("www.") else h


# ------------------------------------------------------------------------------------------------- JSON-LD
def ld_items(texts: list[str]) -> list[dict]:
    """Every object in the page's JSON-LD blocks, nested ones too (@graph, offers, itemListElement ...)."""
    out = []

    def walk(x, depth=0):
        if depth > 8:
            return
        if isinstance(x, list):
            for i in x:
                walk(i, depth + 1)
        elif isinstance(x, dict):
            out.append(x)
            for k in ("@graph", "itemListElement", "item", "mainEntity", "hasOfferCatalog", "itemOffered",
                      "offers", "brand", "publisher", "provider", "author", "isPartOf"):
                if k in x:
                    walk(x[k], depth + 1)
    for t in texts:
        try:
            walk(json.loads(t.strip().rstrip(";")))
        except ValueError:
            continue
    return out


def _types(d: dict) -> set[str]:
    t = d.get("@type")
    return {str(x).lower() for x in (t if isinstance(t, list) else [t]) if x}


def _url_of(v) -> str:
    if isinstance(v, list):
        v = v[0] if v else ""
    if isinstance(v, dict):
        v = v.get("url") or v.get("contentUrl") or v.get("@id") or ""
    return str(v or "")


def price_words(amount, currency: str = "") -> str:
    """29.9, "EUR" -> "29,90 €" (euros with a decimal comma); whole numbers stay whole (200 -> "200 €")."""
    try:
        x = float(str(amount).replace(",", "."))
    except ValueError:
        return _text(amount, 24)
    cur = str(currency or "").upper()
    num = f"{x:.0f}" if x == int(x) else f"{x:.2f}".replace(".", "," if cur == "EUR" else ".")
    pre, post = CURRENCY.get(cur, ("", f" {cur}" if cur else ""))
    return f"{pre}{num}{post}"[:24]


def _offer_price(offers) -> str:
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return ""
    cur = offers.get("priceCurrency") or ""
    if offers.get("price") not in (None, ""):
        return price_words(offers["price"], cur)
    if offers.get("lowPrice") not in (None, ""):                     # an AggregateOffer: "from ..."
        return "from " + price_words(offers["lowPrice"], cur)
    spec = offers.get("priceSpecification")
    if isinstance(spec, dict) and spec.get("price") not in (None, ""):
        return price_words(spec["price"], spec.get("priceCurrency") or cur)
    return ""


def ld_products(items: list[dict], base: str) -> list[dict]:
    out = []
    for d in items:
        ty = _types(d)
        if not ty & {"product", "service", "productgroup", "offer"}:
            continue
        if "offer" in ty and not ty & {"product", "service"}:
            continue                                               # an offer alone: its itemOffered is walked too
        name = _text(d.get("name"), 80)
        if not name:
            continue
        img = _url_of(d.get("image"))
        out.append({"name": name, "what": _text(d.get("description"), 160), "price": _offer_price(d.get("offers")),
                    "url": urllib.parse.urljoin(base, _url_of(d.get("url"))) if d.get("url") else "",
                    "image_url": urllib.parse.urljoin(base, img) if img else "", "from": "jsonld"})
    return out


# ------------------------------------------------------------------------------------------------- colours, fonts
HEX = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-fA-F\w-])")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})")
BRAND_VAR = re.compile(r"--[\w-]*(?:brand|primary|accent|main|secondary|theme)[\w-]*\s*:\s*([^;}{]+)", re.I)


def _hex(s: str) -> str | None:
    s = s.lstrip("#").lower()
    if len(s) in (3, 4):
        s = "".join(c * 2 for c in s[:3])
    elif len(s) in (6, 8):
        s = s[:6]
    else:
        return None
    return "#" + s


def colours(css: str, theme: str = "", n: int = 8) -> list[dict]:
    """The most used colours, near ones merged (the first one kept); theme-color first, brand-named variables x5."""
    count: dict[str, int] = {}

    def add(h, w):
        if h:
            count[h] = count.get(h, 0) + w
    for m in BRAND_VAR.finditer(css):
        v = m.group(1)
        for h in HEX.finditer(v):
            add(_hex(h.group(1)), 5)
        for r in RGB.finditer(v):
            add("#%02x%02x%02x" % tuple(min(255, int(x)) for x in r.groups()), 5)
    for h in HEX.finditer(css):
        add(_hex(h.group(1)), 1)
    for r in RGB.finditer(css):
        add("#%02x%02x%02x" % tuple(min(255, int(x)) for x in r.groups()), 1)
    t = _hex(theme.strip()) if re.fullmatch(r"\s*#[0-9a-fA-F]{3,8}\s*", theme or "") else None
    if t:
        add(t, 1000)
    kept: list[dict] = []
    for h, c in sorted(count.items(), key=lambda kv: -kv[1]):
        rgb = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
        near = next((k for k in kept if sum((a - b) ** 2 for a, b in zip(rgb, k["_rgb"])) < 18 ** 2), None)
        if near:
            near["count"] += c
        else:
            kept.append({"hex": h, "count": c, "_rgb": rgb})
    out = sorted(kept, key=lambda k: -k["count"])[:n]
    for k in out:
        del k["_rgb"]
        k["theme"] = k["hex"] == t
    return out


def _font_names(css: str) -> list[str]:
    names = []
    for m in re.finditer(r"@font-face\s*{[^}]*?font-family\s*:\s*([^;}]+)", css, re.I):
        names.append(m.group(1))
    for m in re.finditer(r"(?<![\w-])font-family\s*:\s*([^;}{]+)", css, re.I):
        names.append(m.group(1).split(",")[0])
    out = []
    for raw in names:
        n = raw.strip().strip("'\"").strip()
        if n and not n.lower().startswith("var(") and n.lower() not in GENERIC_FONTS and len(n) <= 60:
            out.append(n)
    return out


def google_fonts(hrefs: list[str]) -> list[str]:
    out = []
    for h in hrefs:
        if "fonts.googleapis.com" not in h:
            continue
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(h).query)
        for fam in q.get("family", []):
            for f in fam.split("|"):
                out.append(f.split(":")[0].replace("+", " ").strip())
    return [f for f in out if f]


def fonts(css: str, hrefs: list[str], library: list[str]) -> list[dict]:
    """The site's fonts, most used first; library = the name the lab's font folder knows it by (or None)."""
    lib = {re.sub(r"\W", "", f.lower()): f for f in library}
    count: dict[str, dict] = {}
    for f in google_fonts(hrefs):
        count.setdefault(f.lower(), {"family": f, "count": 0, "source": "google"})["count"] += 10
    for f in _font_names(css):
        e = count.setdefault(f.lower(), {"family": f, "count": 0, "source": "site"})
        e["count"] += 1
    out = sorted(count.values(), key=lambda e: -e["count"])[:6]
    for e in out:
        e["library"] = lib.get(re.sub(r"\W", "", e["family"].lower()))
    return out


# ------------------------------------------------------------------------------------------------- the page's look
# (2026-10-25, the user: "how are colours taken from the website import? cuz i think they are missing the good ones ...
# maybe take a screenshot and analize the major colors or the ones they are most distinct?"): what a visitor SEES -
# the home page screenshotted by headless Edge, its colours grouped (k-means in Lab) with the share of the page each
# covers; the logo's own colours; the colours the CSS names as the brand's. Then a palette with roles: the background
# (the biggest), the text (the most contrast with it), up to 3 accents (colourful and distinct - even a small button
# counts: chroma beats area), the other neutrals that cover something.
ROLES = ("background", "text", "accent", "neutral")


def _lab(rgb):
    """sRGB 0..1 (N, 3) -> CIE Lab (N, 3), D65."""
    import numpy as np
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def _de(a, b) -> float:
    return float(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5)


def groups(rgb, k: int = 12, seed: int = 0) -> list[dict]:
    """Pixels (N, 3, 0..255) -> their colour groups, biggest first: {hex, share 0..1, lab, chroma}; near groups
    (ΔE < 10) merged. k-means in Lab with a fixed start (the same picture = the same groups)."""
    import numpy as np
    px = np.asarray(rgb, dtype=np.float64).reshape(-1, 3)
    if len(px) > 60000:
        px = px[np.random.RandomState(seed).choice(len(px), 60000, replace=False)]
    lab = _lab(px / 255)
    rs = np.random.RandomState(seed)
    cent = [lab[rs.randint(len(lab))]]
    for _ in range(min(k, len(lab)) - 1):                 # k-means++: the next start far from the ones there
        d = np.min(((lab[:, None, :] - np.array(cent)[None]) ** 2).sum(2), 1)
        if d.sum() == 0:
            break
        cent.append(lab[rs.choice(len(lab), p=d / d.sum())])
    cent = np.array(cent)
    for _ in range(12):
        lbl = ((lab[:, None, :] - cent[None]) ** 2).sum(2).argmin(1)
        cent = np.array([lab[lbl == i].mean(0) if (lbl == i).any() else cent[i] for i in range(len(cent))])
    lbl = ((lab[:, None, :] - cent[None]) ** 2).sum(2).argmin(1)
    out = []
    for i in range(len(cent)):
        m = lbl == i
        if m.any():
            out.append({"rgb": px[m].mean(0), "lab": tuple(lab[m].mean(0)), "share": float(m.mean())})
    out.sort(key=lambda g: -g["share"])
    merged: list[dict] = []
    for g in out:
        near = next((h for h in merged if _de(h["lab"], g["lab"]) < 10), None)
        if near:
            w = near["share"] + g["share"]
            near["rgb"] = (near["rgb"] * near["share"] + g["rgb"] * g["share"]) / w
            near["share"] = w
        else:
            merged.append(dict(g))
    for g in merged:
        g["hex"] = "#%02x%02x%02x" % tuple(int(round(min(255, max(0, v)))) for v in g["rgb"])
        g["chroma"] = (g["lab"][1] ** 2 + g["lab"][2] ** 2) ** 0.5
        del g["rgb"]
    return sorted(merged, key=lambda g: -g["share"])


def picture_groups(path: Path, k: int = 12) -> list[dict]:
    """A picture's colour groups (its see-through pixels left out); an SVG = the colours its code paints with."""
    p = Path(path)
    if p.suffix.lower() == ".svg":
        txt = p.read_text(encoding="utf-8", errors="replace")
        hexes = [_hex(h) for h in re.findall(r"(?:fill|stroke|stop-color)\s*[:=]\s*[\"']?\s*#([0-9a-fA-F]{3,8})\b", txt)]
        hexes = [h for h in hexes if h]
        out = []
        for h in dict.fromkeys(hexes):
            lab = _lab_of(h)
            out.append({"hex": h, "share": hexes.count(h) / len(hexes), "lab": lab, "chroma": (lab[1] ** 2 + lab[2] ** 2) ** 0.5})
        return sorted(out, key=lambda g: -g["share"])
    import numpy as np
    from PIL import Image
    im = Image.open(p).convert("RGBA")
    im.thumbnail((256, 256))
    a = np.asarray(im)
    px = a[a[..., 3] > 128][:, :3]
    return groups(px, k) if len(px) else []


def _lab_of(h: str):
    import numpy as np
    return tuple(_lab(np.array([[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]]))[0])


def pick_palette(screen: list[dict], logo: list[dict], css: list[str], theme: str = "", n: int = 8,
                 css_all: list[str] | None = None) -> list[dict]:
    """The brand's palette with roles from what was seen: screen = the page's groups (share of the page), logo = the
    logo's groups, css = colours the CSS names as the brand's (+ theme-color), css_all = every colour the CSS uses.
    -> [{hex, role, share, from}] - the background, the text, up to 3 accents, then neutrals that cover >= 1 % of the
    page and the logo's main ones; nothing twice (ΔE < 12). A colour seen on the page takes the CSS' exact value when
    one is near (ΔE < 10: a gradient's average is not the designer's #0e0e10); text too small to measure on the
    screenshot = the CSS' most used neutral that reads on the background."""
    out: list[dict] = []
    exact = [(h, _lab_of(h)) for h in dict.fromkeys(([theme] if theme else []) + list(css) + list(css_all or [])) if h]

    def snap(h, lab):
        near = min(exact, key=lambda e: _de(lab, e[1]), default=None)
        return (near[0], near[1]) if near and _de(lab, near[1]) < 10 else (h, lab)

    def add(h, role, share, src, lab):
        if src == "page":
            h, lab = snap(h, lab)
        if all(_de(lab, o["_lab"]) >= 12 for o in out) and len(out) < n:
            out.append({"hex": h, "role": role, "share": round(share * 100, 1) if share is not None else None,
                        "from": src, "_lab": lab})
            return True
        return False
    if screen:
        bg = screen[0]
        add(bg["hex"], "background", bg["share"], "page", bg["lab"])
        bgl = out[0]["_lab"]
        txt = [g for g in screen[1:] if g["share"] >= 0.003 and g["chroma"] < 20 and abs(g["lab"][0] - bgl[0]) > 35]
        if txt:
            t = max(txt, key=lambda g: abs(g["lab"][0] - bgl[0]))
            add(t["hex"], "text", t["share"], "page", t["lab"])
        else:                                         # small text: the CSS' most used neutral that reads on the background
            css_txt = [(h, lab) for h, lab in exact if (lab[1] ** 2 + lab[2] ** 2) ** 0.5 < 20 and abs(lab[0] - bgl[0]) > 35]
            if css_txt:
                h, lab = css_txt[0]                    # exact = the theme, the brand's, then the CSS' by use
                add(h, "text", None, "css", lab)
    cands = []                                                     # accents: colourful beats big
    for g in screen:
        if g["chroma"] >= 18 and g["share"] >= 0.0015:
            cands.append((min(g["share"], 0.25) ** 0.5 * g["chroma"] / 30, g["hex"], g["share"], "page", g["lab"]))
    for g in logo:
        if g["chroma"] >= 18 and g["share"] >= 0.04:
            cands.append((0.6 + g["share"] * g["chroma"] / 30, g["hex"], None, "logo", g["lab"]))
    for i, h in enumerate(dict.fromkeys([x for x in ([theme] if theme else []) + css if x])):
        lab = _lab_of(h)
        if (lab[1] ** 2 + lab[2] ** 2) ** 0.5 >= 18:
            cands.append((0.5 - i * 0.01, h, None, "css", lab))
    accents = 0
    for _, h, share, src, lab in sorted(cands, key=lambda c: -c[0]):
        if accents < 3 and add(h, "accent", share, src, lab):
            accents += 1
    for g in screen[1:]:                                           # the neutrals that cover something
        if g["share"] >= 0.01:
            add(g["hex"], "neutral", g["share"], "page", g["lab"])
    for g in logo:                                                 # the logo's own main colours (a metal, a tint)
        if g["share"] >= 0.1:
            add(g["hex"], "accent" if g["chroma"] >= 18 else "neutral", None, "logo", g["lab"])
    for o in out:
        del o["_lab"]
    return out


def brand_css(css: str) -> list[str]:
    """The colours the CSS names as the brand's (custom properties called brand / primary / accent / main / theme)."""
    out = []
    for m in BRAND_VAR.finditer(css):
        out += [_hex(h.group(1)) for h in HEX.finditer(m.group(1))]
        out += ["#%02x%02x%02x" % tuple(min(255, int(x)) for x in r.groups()) for r in RGB.finditer(m.group(1))]
    return [h for h in dict.fromkeys(out) if h]


def _edge() -> str | None:
    import os
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        p = Path(base or "") / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if base and p.is_file():
            return str(p)
    return None


def screenshot(url: str, out: Path, width: int = 1440, height: int = 1800) -> Path | None:
    """The page as a visitor sees it (headless Edge, its own empty profile, 30 s at most) -> out (PNG) or None."""
    import subprocess
    import tempfile
    exe = _edge()
    if not exe or not url.startswith("https://"):
        return None
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ml-shot-") as prof:
        try:
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--no-first-run",
                            "--no-default-browser-check", f"--user-data-dir={prof}", f"--window-size={width},{height}",
                            "--virtual-time-budget=6000", f"--screenshot={out}", url],
                           capture_output=True, timeout=40, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired):
            return None
    return out if out.is_file() and out.stat().st_size > 1000 else None


# ------------------------------------------------------------------------------------------------- pages, logos
def social(urls: list[str]) -> list[dict]:
    """The brand's own pages among the links (one per platform, the first found)."""
    out, seen = [], set()
    for u in urls:
        u = u.strip()
        for plat, rx in SOCIAL.items():
            m = re.match(r"https?://" + rx, u, re.I)
            if not m or plat in seen:
                continue
            handle = m.group(0).rstrip("/").rsplit("/", 1)[-1]
            if handle.lstrip("@").lower() in NOT_A_HANDLE:
                continue
            seen.add(plat)
            out.append({"platform": plat, "url": "https://" + m.group(0).split("://", 1)[1].rstrip("/"),
                        "handle": handle if handle.startswith("@") else "@" + handle})
    return out


def logo_urls(page: _Page, items: list[dict], base: str) -> list[dict]:
    """Logo candidates, best first: JSON-LD logo, <img> named logo, apple-touch-icon / big icons, og:image (share)."""
    out = []

    def add(u, kind):
        if u and not u.startswith("data:"):
            u = urllib.parse.urljoin(base, u)
            if u.startswith("https://") and u not in [x["url"] for x in out]:
                out.append({"url": u, "kind": kind})
    for d in items:
        if _types(d) & {"organization", "brand", "localbusiness", "store", "onlinestore", "corporation"} and d.get("logo"):
            add(_url_of(d["logo"]), "logo")
    for a in page.imgs:
        if "logo" in " ".join(a.get(k, "") for k in ("src", "alt", "class", "id")).lower():
            src = a.get("src") or ""
            if a.get("srcset"):                                          # the biggest of the srcset
                cands = [c.strip().split(" ") for c in a["srcset"].split(",") if c.strip()]
                cands = [(c[0], int(re.sub(r"\D", "", c[1]) or 0) if len(c) > 1 else 0) for c in cands]
                src = max(cands, key=lambda c: c[1])[0] if cands else src
            add(src, "logo")
    icons = [a for a in page.links if "icon" in a.get("rel", "").lower()]
    size = lambda a: max([int(x) for x in re.findall(r"(\d+)x\d+", a.get("sizes", ""))] or [0])  # noqa: E731
    for a in sorted(icons, key=lambda a: (("apple-touch" not in a.get("rel", "")), -size(a))):
        if a.get("href", "").lower().split("?")[0].endswith(".ico"):
            continue
        add(a.get("href"), "icon")
    add(page.meta.get("og:image") or page.meta.get("twitter:image") or "", "share")
    return out[:6]


def _sniff(raw: bytes) -> str | None:
    """A picture's extension by its first bytes (an SVG only without scripts), else None."""
    h = raw[:16]
    if h.startswith(b"\x89PNG"):
        return ".png"
    if h.startswith(b"\xff\xd8"):
        return ".jpg"
    if h[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return ".webp"
    txt = raw[:400_000].decode("utf-8", "replace").lower()
    if "<svg" in txt and not re.search(r"<script|<foreignobject|\son\w+\s*=|javascript:", txt):
        return ".svg"
    return None


# ------------------------------------------------------------------------------------------------- the read
class Reader:
    def __init__(self, url: str, log=print, out: Path = IMPORT, get=None, shoot: bool = True):
        u = url.strip()
        if not re.match(r"https?://", u, re.I):
            u = "https://" + u
        self.home = re.sub(r"^http://", "https://", u, flags=re.I)
        if not urllib.parse.urlsplit(self.home).path:
            self.home += "/"
        self.site = _host(self.home)
        self.log, self.out = log, Path(out)
        self._get = get or self._fetch
        self.shoot = shoot                                # False = no screenshot (the self-check: no browser, no network)
        self.robots = None

    def _fetch(self, url: str, accept: str = "text/html,application/xhtml+xml,*/*;q=0.8", limit: int = MAX_BYTES):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
                                                   "Accept-Language": "en,es;q=0.8"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = r.read(limit + 1)
            if len(data) > limit:
                raise ValueError(f"more than {limit // 1_000_000} MB")
            return r.geturl(), r.headers.get("content-type", ""), data

    def _allowed(self, url: str) -> bool:
        if self.robots is None:
            self.robots = urllib.robotparser.RobotFileParser()
            try:
                _, _, raw = self._get(f"https://{urllib.parse.urlsplit(self.home).netloc}/robots.txt", "text/plain", 500_000)
                self.robots.parse(raw.decode("utf-8", "replace").splitlines())
            except Exception:                           # no robots.txt (404) or none readable: everything allowed
                self.robots.parse([])
        return self.robots.can_fetch(ROBOTS_UA, url)

    def _page(self, url: str):
        if not self._allowed(url):
            self.log(f"  robots.txt keeps out {url}")
            return None, None
        try:
            final, ctype, raw = self._get(url)
        except (urllib.error.URLError, OSError, ValueError) as e:
            self.log(f"  could not read {url}: {getattr(e, 'reason', e)}")
            return None, None
        if _host(final) != self.site or "html" not in ctype.lower():
            return None, None
        m = re.search(r"charset=([\w-]+)", ctype)
        try:
            html = raw.decode(m.group(1) if m else "utf-8", "replace")
        except LookupError:                              # a charset Python does not know
            html = raw.decode("utf-8", "replace")
        return final, html

    def _json(self, url: str):
        try:
            if not self._allowed(url):
                return None
            _, ctype, raw = self._get(url, "application/json")
            return json.loads(raw.decode("utf-8", "replace"))
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def _download(self, url: str) -> tuple[bytes, str] | None:
        """A picture's bytes and extension (checked by its first bytes), or None."""
        try:
            if not url.startswith("https://"):
                return None
            _, _, raw = self._get(url, "image/*", MAX_PIC)
        except (urllib.error.URLError, OSError, ValueError):
            return None
        ext = _sniff(raw)
        return (raw, ext) if ext else None

    def _save(self, raw: bytes, ext: str, name: str) -> str:
        """Written to the import folder (an earlier import's file of the same name is overwritten - found.json names
        the files of the newest one); its lab-relative path (absolute outside the lab: the self-check)."""
        f = self.out / f"{name}{ext}"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(raw)
        return f.relative_to(LAB).as_posix() if LAB in f.parents else f.as_posix()

    def google_font(self, family: str) -> dict | None:
        """A font the site uses that the lab's library lacks, when it is a Google font (free: OFL / Apache): its TTF
        files (400-700, static) and its licence downloaded to import\\fonts\\<dir>\\; None when Google does not have it."""
        q = urllib.parse.quote_plus(family)
        css = None
        for axis in (":wght@400;500;600;700", ":wght@400;700", ""):         # a family without those weights: fewer
            try:
                _, _, raw = self._get(f"https://fonts.googleapis.com/css2?family={q}{axis}", "text/css", 200_000)
                css = raw.decode("utf-8", "replace")
                break
            except (urllib.error.URLError, OSError, ValueError):
                continue
        faces = re.findall(r"font-weight:\s*(\d+);[^}]*?src:\s*url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css or "")
        if not faces:
            return None
        gid = re.sub(r"[^a-z0-9]", "", family.lower())
        lic = None
        for path, name in ((f"ofl/{gid}/OFL.txt", "OFL.txt"), (f"apache/{gid}/LICENSE.txt", "LICENSE.txt"),
                           (f"ufl/{gid}/UFL.txt", "LICENSE.txt")):
            try:
                _, _, raw = self._get("https://raw.githubusercontent.com/google/fonts/main/" + path, "text/plain", 200_000)
                lic = (name, raw)
                break
            except (urllib.error.URLError, OSError, ValueError):
                continue
        if not lic:                                       # no licence found: never brought in
            return None
        d = self.out / "fonts" / re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")
        files = []
        for w, u in dict(faces).items():                   # one file a weight
            try:
                _, _, raw = self._get(u, "font/ttf", 3_000_000)
            except (urllib.error.URLError, OSError, ValueError):
                continue
            if raw[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO"):
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{family.replace(' ', '')}-{w}.ttf").write_bytes(raw)
                files.append(int(w))
        if not files:
            return None
        (d / lic[0]).write_bytes(lic[1])
        rel = d.relative_to(LAB).as_posix() if LAB in d.parents else d.as_posix()
        return {"dir": rel, "weights": sorted(files), "licence": "OFL" if lic[0] == "OFL.txt" else "Apache 2.0"}

    def shop(self, html: str) -> tuple[str | None, list[dict]]:
        root = f"https://{urllib.parse.urlsplit(self.home).netloc}"
        if "cdn.shopify.com" in html or "Shopify.shop" in html:
            data = self._json(root + "/products.json?limit=250")
            if isinstance(data, dict) and isinstance(data.get("products"), list):
                m = re.search(r'Shopify\.currency\s*=\s*{\s*"active"\s*:\s*"(\w{3})"', html) \
                    or re.search(r'"currencyCode"\s*:\s*"(\w{3})"', html) \
                    or re.search(r'product:price:currency"\s+content="(\w{3})"', html)
                cur = m.group(1) if m else ""
                out = []
                for p in data["products"][:MAX_PRODUCTS]:
                    prices = sorted({float(v.get("price") or 0) for v in p.get("variants") or [] if v.get("price")})
                    price = (("from " if len(prices) > 1 else "") + price_words(prices[0], cur)) if prices else ""
                    imgs = p.get("images") or []
                    out.append({"name": _text(p.get("title"), 80), "what": _text(p.get("body_html"), 160),
                                "price": price, "url": f"{root}/products/{p.get('handle', '')}",
                                "image_url": (imgs[0] or {}).get("src", "") if imgs else "", "from": "shopify"})
                return "shopify", [p for p in out if p["name"]]
        if "woocommerce" in html.lower() or "wp-content" in html:
            data = self._json(root + "/wp-json/wc/store/v1/products?per_page=100") \
                or self._json(root + "/wp-json/wc/store/products?per_page=100")
            if isinstance(data, list) and data:
                out = []
                for p in data[:MAX_PRODUCTS]:
                    pr = p.get("prices") or {}
                    price = ""
                    if pr.get("price") not in (None, ""):
                        try:
                            amount = int(pr["price"]) / 10 ** int(pr.get("currency_minor_unit", 2))
                            price = price_words(amount, pr.get("currency_code", ""))
                        except (TypeError, ValueError):
                            price = ""
                    imgs = p.get("images") or []
                    out.append({"name": _text(p.get("name"), 80),
                                "what": _text(p.get("short_description") or p.get("description"), 160),
                                "price": price, "url": p.get("permalink", ""),
                                "image_url": (imgs[0] or {}).get("src", "") if imgs else "", "from": "woocommerce"})
                return "woocommerce", [p for p in out if p["name"]]
        return None, []

    def progress(self, pct: int, stage: str) -> None:
        """A line the app's progress bar reads: "progress <0-100> <stage>" (home, pages, styles, shop, fonts, logos,
        pictures, done)."""
        self.log(f"progress {int(pct)} {stage}")

    def read(self) -> dict:
        t0 = time.time()
        self.log(f"Reading {self.home}")
        self.progress(3, "home")
        final, html = self._page(self.home)
        if not html:
            raise RuntimeError(f"could not read {self.home} - is the address right and the site online?")
        pages = [(final, html)]
        home = parse(html)
        links = []
        for h in home.hrefs:
            u = urllib.parse.urljoin(final, h).split("#")[0]
            if u.startswith("https://") and _host(u) == self.site and u.rstrip("/") != final.rstrip("/") \
                    and not SKIP_EXT.search(u) and LIKELY.search(urllib.parse.urlsplit(u).path) and u not in links:
                links.append(u)
        todo = links[:MAX_PAGES - 1]
        self.progress(15, "pages")
        for i, u in enumerate(todo):
            f, h = self._page(u)
            if h:
                pages.append((f, h))
                self.log(f"  read {f}")
            self.progress(15 + 35 * (i + 1) / len(todo), "pages")
        self.progress(52, "styles")
        parsed = [(u, parse(h)) for u, h in pages]
        css = "\n".join(s for _, p in parsed for s in p.styles + p.inline)
        sheets = []
        for a in home.links:
            if "stylesheet" in a.get("rel", "").lower() and a.get("href"):
                u = urllib.parse.urljoin(final, a["href"])
                if _host(u) == self.site and u.startswith("https://"):
                    sheets.append(u)
        for u in sheets[:MAX_CSS]:
            try:
                _, _, raw = self._get(u, "text/css", MAX_BYTES)
                css += "\n" + raw.decode("utf-8", "replace")
            except (urllib.error.URLError, OSError, ValueError):
                pass
        items = [d for u, p in parsed for d in ld_items(p.ld)]
        org = next((d for d in items if _types(d) & {"organization", "brand", "localbusiness", "store", "onlinestore",
                                                     "corporation", "website"} and d.get("name")), {})
        name = _text(home.meta.get("og:site_name") or org.get("name") or re.split(r"\s[|·–—-]\s", home.title)[0], 80)
        about = _text(home.meta.get("description") or home.meta.get("og:description") or org.get("description"), 300)
        if re.fullmatch(r"(?i)coming soon\.?|under construction\.?|home", about or ""):
            about = ""
        self.progress(58, "shop")
        shop, products = self.shop(html)
        for u, p in parsed:
            products += ld_products(ld_items(p.ld), u)
            if p.meta.get("product:price:amount") and p.meta.get("og:title"):
                products.append({"name": _text(p.meta["og:title"], 80), "what": _text(p.meta.get("og:description"), 160),
                                 "price": price_words(p.meta["product:price:amount"], p.meta.get("product:price:currency", "")),
                                 "url": u, "image_url": p.meta.get("og:image", ""), "from": "og"})
        seen, prods = set(), []
        for p in products:
            k = p["name"].lower()
            if k not in seen:
                seen.add(k)
                prods.append(p)
        prods = prods[:MAX_PRODUCTS]
        if prods:
            self.log(f"  {len(prods)} product(s) found ({shop or 'from the pages'})")
        from . import fonts as F
        library = [f["family"] for f in F.families()]
        hrefs = [a.get("href", "") for _, p in parsed for a in p.links]
        found_fonts = fonts(css, hrefs, library)
        self.progress(64, "fonts")
        for f in [f for f in found_fonts if not f["library"]][:3]:
            f["google"] = self.google_font(f["family"])
            if f["google"]:
                self.log(f"  {f['family']}: a free Google font ({f['google']['licence']}) - can come into your fonts")
        theme = home.meta.get("theme-color", "")
        theme = _hex(theme.strip()) if re.fullmatch(r"\s*#[0-9a-fA-F]{3,8}\s*", theme or "") else ""
        anchors = [urllib.parse.urljoin(u, h) for u, p in parsed for h in p.hrefs]
        same_as = [x for d in items for x in (d.get("sameAs") if isinstance(d.get("sameAs"), list) else [d.get("sameAs")])
                   if isinstance(x, str)]
        pages_found = social(same_as + anchors)
        placeholders = sorted({plat for a in anchors for plat, rx in SOCIAL.items()
                               if (m := re.match(r"https?://" + rx, a, re.I))
                               and m.group(0).rstrip("/").rsplit("/", 1)[-1].lstrip("@").lower() in PLACEHOLDERS}
                              - {x["platform"] for x in pages_found})
        logos, digests = [], set()
        self.progress(72, "logos")
        for c in logo_urls(home, items, final):
            got = self._download(c["url"])
            if got and hashlib.sha1(got[0]).hexdigest() not in digests:
                digests.add(hashlib.sha1(got[0]).hexdigest())
                logos.append({**c, "file": self._save(*got, f"logo_{len(logos) + 1}")})
        # the colours: what the page shows (a screenshot) + the logo's + the CSS' brand ones -> a palette with roles;
        # no Edge / no screenshot = the CSS' most used colours, as before
        self.progress(76, "screen")
        shot = screenshot(final, self.out / "page.png") if self.shoot else None
        screen, logo_g = [], []
        if shot:
            import numpy as np
            from PIL import Image
            im = Image.open(shot).convert("RGB")
            im.thumbnail((360, 450))
            screen = groups(np.asarray(im).reshape(-1, 3))
            self.log(f"  the page looked at: {len(screen)} colour groups")
        lg = next((x for x in logos if x["kind"] == "logo"), None) or next((x for x in logos if x["kind"] == "icon"), None)
        if lg:
            try:
                logo_g = picture_groups(LAB / lg["file"])
            except (OSError, ValueError):
                logo_g = []
        if screen:
            cols = pick_palette(screen, logo_g, brand_css(css), theme, css_all=[c["hex"] for c in colours(css, theme, 20)])
        else:
            cols = [{**c, "role": "", "share": None, "from": "css"} for c in colours(css, theme)]
        for c in cols:
            c["theme"] = c["hex"] == theme
        self.progress(82, "pictures")
        for i, p in enumerate(prods):
            got = self._download(p["image_url"]) if p.get("image_url") else None
            p["image"] = self._save(*got, f"product_{i + 1}") if got else None
            self.progress(82 + 16 * (i + 1) / len(prods), "pictures")
        text, n_text = site_text(parsed)
        found = {"text": text, "text_blocks": n_text,
                 "url": self.home, "site": self.site, "at": time.strftime("%Y-%m-%d %H:%M:%S"),   # seconds: one import =
                 # one "at" (the page tells a new import from one put aside or taken by it)
                 "pages_read": [u for u, _ in pages], "name": name, "about": about, "colours": cols,
                 "screenshot": (shot.relative_to(LAB).as_posix() if LAB in shot.parents else shot.as_posix()) if shot else None,
                 "fonts": found_fonts, "logos": logos, "pages": pages_found, "placeholders": placeholders,
                 "shop": shop, "products": prods, "seconds": round(time.time() - t0, 1)}
        self.out.mkdir(parents=True, exist_ok=True)
        tmp = self.out / "found.json.tmp"
        tmp.write_text(json.dumps(found, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.out / "found.json")
        self.progress(100, "done")
        self.log(f"Found: name {name!r}, {len(cols)} colour(s), {len(found_fonts)} font(s), {len(logos)} logo picture(s), "
                 f"{len(pages_found)} page(s), {len(prods)} product(s) - {len(pages)} page(s) read in {found['seconds']} s")
        return found


def read(url: str, log=print, out: Path = IMPORT) -> dict:
    return Reader(url, log, out).read()


def load(out: Path = IMPORT) -> dict | None:
    try:
        return json.loads((Path(out) / "found.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------------------------------------- self-check
SHOP_HOME = """<!doctype html><html><head><title>Kutxiletto | Knives made by hand</title>
<meta name="description" content="Hand-forged kitchen knives from the Basque Country.">
<meta property="og:site_name" content="Kutxiletto"><meta name="theme-color" content="#2EAA5C">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png"><link rel="icon" href="/favicon.ico">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter&display=swap">
<style>:root{--brand-primary:#2eaa5c;--text:#111}body{font-family:"Inter",sans-serif;color:#111;background:#fff}
h1{font-family:'Space Grotesk', system-ui;color:#2EAA5C}.btn{background:rgb(46,170,92)}</style>
<script>window.Shopify = {}; Shopify.shop = "kutx.myshopify.com"; Shopify.currency = {"active":"EUR","rate":"1.0"};</script>
<script src="https://cdn.shopify.com/s/x.js"></script></head><body>
<img class="header__logo" src="/logo.svg" alt="Kutxiletto">
<a href="/collections/all">Shop</a><a href="/pages/about">About</a><a href="/blog/news">Blog</a>
<a href="https://www.instagram.com/kutxiletto/">IG</a><a href="https://www.tiktok.com/@kutxiletto">TikTok</a>
<a href="https://twitter.com/intent/tweet?text=x">share</a><a href="https://www.youtube.com/@HANDLE">yt</a>
</body></html>"""
SHOP_JSON = {"products": [
    {"title": "Origin", "handle": "origin", "body_html": "<p>A <b>chef's</b> knife, 21 cm.</p>",
     "variants": [{"price": "129.90"}, {"price": "149.90"}], "images": [{"src": "https://cdn.shopify.com/origin.png"}]},
    {"title": "Pioneer", "handle": "pioneer", "body_html": "", "variants": [{"price": "89.00"}], "images": []}]}
LD_PAGE = """<html><head><title>Services - Rift</title><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"Organization","name":"RIFT","logo":"https://rift.example/l.png",
"sameAs":["https://www.youtube.com/@riftshoots","https://www.instagram.com/p/abc"]},
{"@type":"Service","name":"Music video","description":"A full music video, one day of filming.",
"offers":{"@type":"Offer","price":"200","priceCurrency":"EUR"}},
{"@type":"Product","name":"Short cinematic video","offers":{"@type":"AggregateOffer","lowPrice":"50","priceCurrency":"USD"}}]}
</script></head><body></body></html>"""
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


def selfcheck() -> dict:
    """The parsers and one whole read of a made-up shop (no network). {passed, seconds, lines}."""
    import tempfile
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    case("price words: 29.9 EUR -> 29,90 €, 200 USD -> $200, 9.5 USD -> $9.50",
         price_words(29.9, "EUR") == "29,90 €" and price_words("200", "usd") == "$200" and price_words("9.5", "USD") == "$9.50")
    cs = colours("a{color:#FFF}b{color:#fff}c{color:#fefefe}d{color:#2eaa5c}--brand-accent: #ff6600;", "#0e0e10")
    case("colours: theme-color first, near ones merged, a brand variable counts more",
         [c["hex"] for c in cs] == ["#0e0e10", "#ff6600", "#ffffff", "#2eaa5c"] and cs[2]["count"] == 3 and cs[0]["theme"])
    fs = fonts('h1{font-family:"Instrument Sans",sans-serif} p{font-family: var(--f), Arial} @font-face{font-family:"Instrument Sans";src:url(x)}',
               ["https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500&family=Inter&display=swap"],
               ["Space Grotesk", "Inter", "Anton"])
    case("fonts: Google Fonts first, generic / var() left out, the library's name found",
         [(f["family"], f["library"]) for f in fs] == [("Space Grotesk", "Space Grotesk"), ("Inter", "Inter"), ("Instrument Sans", None)])
    so = social(["https://www.instagram.com/HANDLE/", "https://twitter.com/intent/tweet", "https://www.tiktok.com/@rift.shoots",
                 "https://www.instagram.com/riftshoots/", "https://www.instagram.com/other/", "https://youtube.com/watch?v=x"])
    case("pages: one per platform, placeholders / share links / posts left out",
         so == [{"platform": "tiktok", "url": "https://www.tiktok.com/@rift.shoots", "handle": "@rift.shoots"},
                {"platform": "instagram", "url": "https://www.instagram.com/riftshoots", "handle": "@riftshoots"}])
    p = parse(LD_PAGE)
    pr = ld_products(ld_items(p.ld), "https://rift.example/services")
    case("JSON-LD: a Service and a Product with their prices (an AggregateOffer = from ...)",
         [(x["name"], x["price"]) for x in pr] == [("Music video", "200 €"), ("Short cinematic video", "from $50")])
    import numpy as np
    page = np.zeros((200, 100, 3), np.uint8)
    page[:] = (14, 14, 16)                                   # the background, most of the page
    page[20:40, 10:90] = (236, 235, 232)                     # the text / a light block
    page[60:100, 0:100] = (43, 44, 49)                       # a panel
    page[150:154, 40:60] = (255, 102, 0)                     # a small orange button (0.4 % of the page)
    pal = pick_palette(groups(page.reshape(-1, 3)), [{"hex": "#2eaa5c", "lab": _lab_of("#2eaa5c"), "share": 0.5,
                                                      "chroma": 50}], ["#2eaa5c", "#ff6600"], "#0e0e10")
    roles = {p["role"]: p["hex"] for p in pal if p["role"] != "accent"}
    acc = [p["hex"] for p in pal if p["role"] == "accent"]
    case(f"the page's colours with roles: background, text, the small orange button and the logo's green as accents, "
         f"the panel a neutral ({[(p['hex'], p['role']) for p in pal]})",
         roles.get("background") == "#0e0e10" and roles.get("text") == "#ecebe8" and roles.get("neutral") == "#2b2c31"
         and "#ff6600" in acc and "#2eaa5c" in acc and len(acc) == 2)
    dark = np.zeros((200, 100, 3), np.uint8)
    dark[:] = (24, 25, 28)                                   # a dark gradient's average, no text big enough to measure
    dark[100:, :] = (48, 50, 55)
    pal = pick_palette(groups(dark.reshape(-1, 3)), [{"hex": "#a7adbd", "lab": _lab_of("#a7adbd"), "share": 0.6, "chroma": 8}],
                       [], "#0e0e10", css_all=["#ecebe8", "#2b2c31", "#8a8a90"])
    case(f"a dark page: the CSS' exact values when near (#0e0e10 for the gradient), the text from the CSS, the logo's "
         f"silver ({[(p['hex'], p['role'], p['from']) for p in pal]})",
         [(p["hex"], p["role"]) for p in pal][:2] == [("#0e0e10", "background"), ("#ecebe8", "text")]
         and ("#a7adbd", "neutral") in [(p["hex"], p["role"]) for p in pal])
    pa = parse("<html><head><title>Services - Rift</title></head><body><nav><a>Home</a><p>Menu text that is long enough</p></nav>"
               "<h1>Music videos</h1><p>We shoot music videos in one day, <br>colour graded and ready to post.</p>"
               "<ul><li>One day of filming with two cameras</li><li>Short</li></ul><div>We use cookies to improve your visit, ok?</div>"
               "<p>We use cookies to make the site better for you.</p><footer><p>RIFT 2026 - all rights reserved here</p></footer></body></html>")
    pb = parse("<html><head><title>About</title></head><body><h2>Who we are</h2><p>Robert Iftimie, a director in Spain.</p></body></html>")
    md, nb = site_text([("https://rift.example/services", pa), ("https://rift.example/about", pb)])
    case("what the website says: headings, paragraphs, list items by page; menus, footers, cookie notes, scraps left out",
         "## Services - Rift" in md and "### Music videos" in md and "We shoot music videos in one day, colour graded and ready to post." in md
         and "- One day of filming with two cameras" in md and "- Short\n" not in md
         and "Menu text" not in md and "cookies" not in md and "all rights" not in md and "## About" in md and nb == 5)
    case("a picture is checked by its first bytes (an SVG with a script is refused)",
         _sniff(PNG) == ".png" and _sniff(SVG) == ".svg" and _sniff(b"<svg onload=alert(1)>") is None and _sniff(b"GIF89a") is None)
    web = {"https://kutx.example/": ("text/html; charset=utf-8", SHOP_HOME.encode()),
           "https://kutx.example/robots.txt": ("text/plain", b"User-agent: *\nDisallow: /pages/\n"),
           "https://kutx.example/collections/all": ("text/html", LD_PAGE.replace("rift.example", "kutx.example").encode()),
           "https://kutx.example/products.json?limit=250": ("application/json", json.dumps(SHOP_JSON).encode()),
           "https://kutx.example/logo.svg": ("image/svg+xml", SVG),
           "https://kutx.example/apple-touch-icon.png": ("image/png", PNG),
           "https://kutx.example/l.png": ("image/png", PNG),
           "https://cdn.shopify.com/origin.png": ("image/png", PNG + b"x")}
    asked = []

    def fake(url, accept="", limit=MAX_BYTES):
        asked.append(url)
        if url not in web:
            raise urllib.error.URLError("404")
        return url, *web[url]
    with tempfile.TemporaryDirectory() as td:
        log = []
        r = Reader("kutx.example", log.append, Path(td), get=fake, shoot=False)
        f = r.read()
        case("a whole read: https added, the name, the about, robots.txt obeyed (/pages/ not read), the blog skipped",
             f["url"] == "https://kutx.example/" and f["name"] == "Kutxiletto" and f["about"].startswith("Hand-forged")
             and "https://kutx.example/pages/about" not in asked and not any("blog" in u for u in asked))
        case("a whole read: the Shopify catalogue with prices in euros, then the pages' JSON-LD ones",
             [(x["name"], x["price"], x["from"]) for x in f["products"]] ==
             [("Origin", "from 129,90 €", "shopify"), ("Pioneer", "89 €", "shopify"),
              ("Music video", "200 €", "jsonld"), ("Short cinematic video", "from $50", "jsonld")]
             and f["products"][0]["what"] == "A chef's knife, 21 cm." and f["products"][0]["image"]
             and f["products"][1]["image"] is None)
        case("a whole read: the theme colour and the brand green, the fonts, the pages (JSON-LD sameAs first, the post "
             "and the @HANDLE / share links left out)",
             f["colours"][0]["hex"] == "#2eaa5c" and [x["family"] for x in f["fonts"]][:2] == ["Space Grotesk", "Inter"]
             and [x["platform"] for x in f["pages"]] == ["youtube", "instagram", "tiktok"]
             and f["pages"][0]["url"] == "https://www.youtube.com/@riftshoots" and f["placeholders"] == [])
        case("a whole read: logos downloaded and checked, the same picture twice kept once",
             [x["kind"] for x in f["logos"]] == ["logo", "logo"] and f["logos"][1]["file"].endswith("logo_2.svg"))
        case("found.json written beside the pictures", load(Path(td)) == f)
        web["https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700"] = (
            "text/css", b"@font-face { font-family: 'Instrument Sans'; font-weight: 400; src: url(https://fonts.gstatic.com/s/is/a.ttf) format('truetype'); }\n"
                        b"@font-face { font-family: 'Instrument Sans'; font-weight: 700; src: url(https://fonts.gstatic.com/s/is/b.ttf) format('truetype'); }")
        web["https://fonts.gstatic.com/s/is/a.ttf"] = ("font/ttf", b"\x00\x01\x00\x00" + b"\x00" * 60)
        web["https://fonts.gstatic.com/s/is/b.ttf"] = ("font/ttf", b"<html>not a font</html>")
        web["https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentsans/OFL.txt"] = ("text/plain", b"SIL OPEN FONT LICENSE Version 1.1")
        g = r.google_font("Instrument Sans")
        case("a Google font the site uses: its TTFs (a file that is no font left out) + its OFL licence; one Google lacks = None",
             g and g["weights"] == [400] and g["licence"] == "OFL" and (Path(g["dir"]) / "OFL.txt").is_file()
             and (Path(g["dir"]) / "InstrumentSans-400.ttf").is_file() and r.google_font("Comic Doom Sans") is None)
        try:
            Reader("nowhere.example", log.append, Path(td), get=fake, shoot=False).read()
            bad = False
        except RuntimeError:
            bad = True
        case("a site that cannot be read: a clear error, nothing written over", bad and load(Path(td)) == f)
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}
