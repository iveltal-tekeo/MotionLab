"""Looks (2026-10-18): design tokens the look-aware Motion Graphics templates take their colours, fonts, corners,
shadow, film grain and easing from - so a template keeps its motion and changes its skin.

    tools\\overlays\\motion\\_looks\\<id>.json   a look (in the repo): name, what, fonts {display, body, accent},
                                              palette {ink, paper, signal, deep, mustard}, radius (px at a 1080-px
                                              short side), shadow (0 = none, 1 = soft and low, 2 = deeper), grain (%)
                                              and - in the default look - motion (GSAP eases: enter, exit, move...)
    tools\\overlays\\motion\\_looks\\index.json  {"default": "<id>", "order": [...]} - the look new templates start in

A look-aware template declares the token settings (TOKENS: display_font, body_font, accent_font, ink, paper, signal,
deep, mustard, radius, shadow, grain) with the default look's values and loads assets/looks/look.css +
assets/looks/looks.js (MLLook: apply(root, V, U) sets the CSS variables --ink ... --font-display ... --radius
--shadow --grain --u, grain(root, tl, opts) adds the moving film grain, EASE = the default look's eases). Switching
looks = setting those settings (presets(): one ready-made look per look file - the app's Look row, overlay.py
preset). ensure(folder) writes the two shared files into a graphic before a render / snapshot; the app serves the
same at /looks.css and /looks.js for live previews.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .util import LAB

LOOKS = LAB / "tools" / "overlays" / "motion" / "_looks"
LINK_CSS = '<link rel="stylesheet" href="assets/looks/look.css">'
LINK_JS = '<script src="assets/looks/looks.js"></script>'
COLOURS = ("ink", "paper", "signal", "deep", "mustard")
FONTS = ("display", "body", "accent")
FALLBACK = {"display": "Georgia, serif", "body": "'Segoe UI', sans-serif", "accent": "Consolas, monospace"}
EASES = {"enter": "expo.out", "exit": "expo.in", "move": "expo.inOut", "settle": "power3.out", "pop": "back.out(1.4)",
         "bounce": "back.out(2.2)"}
# GSAP ease -> the closest CSS cubic-bezier (look.css names them for CSS transitions / keyframes)
BEZIER = {"expo.out": "0.16, 1, 0.3, 1", "expo.in": "0.7, 0, 0.84, 0", "expo.inOut": "0.87, 0, 0.13, 1",
          "power3.out": "0.33, 1, 0.68, 1", "power3.in": "0.32, 0, 0.67, 0", "power3.inOut": "0.65, 0, 0.35, 1",
          "power2.out": "0.5, 1, 0.89, 1", "back.out(1.4)": "0.34, 1.4, 0.64, 1", "back.out(2.2)": "0.34, 1.8, 0.64, 1",
          "none": "0, 0, 1, 1"}


def _read(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def index() -> dict:
    p = LOOKS / "index.json"
    d = _read(p) if p.exists() else {}
    ids = [q.stem for q in sorted(LOOKS.glob("*.json")) if not q.stem.startswith("_") and q.stem != "index"]
    order = [i for i in d.get("order", []) if i in ids] + [i for i in ids if i not in d.get("order", [])]
    default = d.get("default") if d.get("default") in ids else ("my_look" if "my_look" in ids else (order or [""])[0])
    return {"default": default, "order": order}


def all_looks() -> dict:
    """{id: look} in the order of index.json, the default first."""
    ix = index()
    ids = [ix["default"]] + [i for i in ix["order"] if i != ix["default"]]
    return {i: _read(LOOKS / f"{i}.json") | {"id": i} for i in ids if i}


def default() -> dict:
    return all_looks()[index()["default"]]


def motion() -> dict:
    """The eases every look-aware template uses (the default look's "motion", else the built-in confident ones)."""
    m = default().get("motion") or {}
    return {k: str(m.get(k) or v) for k, v in EASES.items()}


def values(look: dict) -> dict:
    """A look as the template settings it sets."""
    out = {f"{k}_font": look["fonts"][k] for k in FONTS}
    out |= {k: look["palette"][k].upper() if isinstance(look["palette"][k], str) else look["palette"][k] for k in COLOURS}
    out |= {"radius": look.get("radius", 14), "shadow": look.get("shadow", 1), "grain": look.get("grain", 0)}
    return out


TOKENS = tuple(f"{k}_font" for k in FONTS) + COLOURS + ("radius", "shadow", "grain")


def declarations(look: dict | None = None) -> list[dict]:
    """The token settings a look-aware template declares (data-composition-variables), defaults = the look."""
    v = values(look or default())
    lab = {"display": "Headline font", "body": "Text font", "accent": "Label font (small caps, numbers)"}
    out = [{"id": f"{k}_font", "type": "enum", "label": lab[k], "default": v[f"{k}_font"], "options": []} for k in FONTS]
    names = {"ink": "Ink (text)", "paper": "Paper (background)", "signal": "Signal (accent)", "deep": "Deep (second colour)",
             "mustard": "Mustard (highlight)"}
    out += [{"id": k, "type": "color", "label": names[k], "default": v[k]} for k in COLOURS]
    out += [{"id": "radius", "type": "number", "label": "Corners (px)", "default": v["radius"], "min": 0, "max": 80, "step": 1},
            {"id": "shadow", "type": "number", "label": "Shadow (0 = none, 1 = soft and low)", "default": v["shadow"],
             "min": 0, "max": 3, "step": 0.1},
            {"id": "grain", "type": "number", "label": "Film grain (%)", "default": v["grain"], "min": 0, "max": 40, "step": 1}]
    return out


def presets() -> dict:
    """One ready-made look per look file, in overlay_settings.presets()' shape (without "active")."""
    return {i: {"label": lk.get("name", i), "what": lk.get("what", ""), "values": values(lk)}
            for i, lk in all_looks().items()}


def is_look_aware(folder: Path) -> bool:
    idx = Path(folder) / "index.html"
    return idx.exists() and "assets/looks/looks.js" in idx.read_text(encoding="utf-8", errors="replace")


# --------------------------------------------------------------------------------------------- the shared files
def css() -> str:
    """look.css: the default look as CSS variables (a template's settings override them on its root) + named easings
    + the classes templates share."""
    lk, m = default(), motion()
    v = values(lk)
    lines = ["/* MotionLab look tokens (generated from tools\\overlays\\motion\\_looks by tools\\motionlab\\looks.py -",
             f"   default look: {lk['id']}). MLLook.apply() sets the same variables from a template's settings. */",
             ":root {"]
    lines += [f"  --{k}: {v[k]};" for k in COLOURS]
    lines += [f"  --font-{k}: '{v[k + '_font']}', {FALLBACK[k]};" for k in FONTS]
    lines += ["  --u: 1px;", f"  --radius: {v['radius']}px;",
              "  --shadow: 0 4px 16px rgba(20, 18, 15, 0.12), 0 1px 3px rgba(20, 18, 15, 0.08);",
              f"  --grain: {v['grain'] / 100:g};"]
    lines += [f"  --ease-{k}: cubic-bezier({BEZIER.get(e, BEZIER['power3.out'])});" for k, e in m.items()]
    lines += ["}",
              ".ml-display { font-family: var(--font-display); font-weight: 400; }",
              ".ml-body { font-family: var(--font-body); }",
              ".ml-accent { font-family: var(--font-accent); letter-spacing: 0.04em; }",
              ".ml-card { background: var(--paper); color: var(--ink); border-radius: var(--radius); box-shadow: var(--shadow); }",
              ".ml-grain { position: absolute; inset: 0; pointer-events: none; opacity: var(--grain); mix-blend-mode: overlay;"
              " background-repeat: repeat; }",
              ".ml-media { position: absolute; overflow: hidden; border-radius: var(--radius); background: var(--deep); }",
              ".ml-media > img, .ml-media > video { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }",
              ""]
    return "\n".join(lines)


_JS = r"""/* MotionLab looks (generated by tools\motionlab\looks.py): MLLook.apply(root, V, U) = the look's tokens from a
   template's settings as CSS variables on its root; MLLook.grain(root, tl, {fps, frames, at, U, seed}) = moving
   film grain (seeded, the same in a preview, a snapshot and a render); MLLook.EASE = the eases of the look;
   MLLook.media(box, src, {fit, focus, kind}) = a media slot: a picture / video of the user's, cover or contain at a
   focus point, else a neutral placeholder in the look.
   The effects toolkit (all seek-safe): rich(el, text) = *bold* _italic_ ==highlight== ^signal^ as word spans
   (+ mark() draws a highlight); handheld(wrapper, tl, {amount 0-10, hits}) = a camera held by hand; grid(parent, tl,
   {kind flat|dots|floor, flow}) = depth behind; glow(el, colour, 0-100, {kind box|text|drop}); liquid(fill, tl) =
   a wobbling meniscus + flowing light in a growing fill; sheet(parent, {w, h, strips}) .setBend(deg) = a bent page
   in 3D, shaded strip by strip; every(tl, {fps, from, to}, fn(t)) = run fn at each frame's time. */
window.MLLook = (() => {
  const EASE = __EASE__;
  const DEF = __DEF__;
  const FB = __FB__;
  const val = (V, k) => (V && V[k] !== undefined && V[k] !== null && V[k] !== "") ? V[k] : DEF[k];
  const rgb = h => { const s = String(h).replace("#", ""); const t = s.length === 3 ? s.split("").map(c => c + c).join("") : s;
    return [0, 2, 4].map(i => parseInt(t.slice(i, i + 2), 16) || 0); };
  const lum = h => { const [r, g, b] = rgb(h); return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255; };
  const rgba = (h, a) => { const [r, g, b] = rgb(h); return `rgba(${r}, ${g}, ${b}, ${a})`; };
  function apply(root, V, U) {
    U = U || 1;
    const s = root.style;
    ["ink", "paper", "signal", "deep", "mustard"].forEach(k => s.setProperty("--" + k, val(V, k)));
    ["display", "body", "accent"].forEach(k => s.setProperty("--font-" + k, `'${val(V, k + "_font")}', ${FB[k]}`));
    s.setProperty("--u", U + "px");
    s.setProperty("--radius", Number(val(V, "radius")) * U + "px");
    const sh = Number(val(V, "shadow")), dark = lum(val(V, "paper")) < 0.35;
    const c = dark ? "#000000" : val(V, "ink");
    const shadow = sh > 0 ? `0 ${4 * sh * U}px ${16 * sh * U}px ${rgba(c, (dark ? 0.35 : 0.10) + 0.03 * sh)}, 0 ${sh * U}px ${3 * sh * U}px ${rgba(c, dark ? 0.3 : 0.08)}` : "none";
    s.setProperty("--shadow", shadow);
    s.setProperty("--grain", String(Number(val(V, "grain")) / 100));
    // radius and shadow also come back resolved: HyperFrames' render drops border-radius: var(--radius) from a
    // stylesheet (seen 2026-10-18; colours and fonts through var() render fine) - set them inline (MLLook.card)
    return {dark, ink: val(V, "ink"), paper: val(V, "paper"), signal: val(V, "signal"), deep: val(V, "deep"),
            mustard: val(V, "mustard"), radius: Number(val(V, "radius")) * U, shadow, rgba};
  }
  // corners + shadow of the look, inline (r: a radius in px instead of the look's; shadow false = none)
  function card(el, L, o) {
    o = o || {};
    el.style.borderRadius = `${o.r !== undefined ? o.r : L.radius}px`;
    if (o.shadow !== false) el.style.boxShadow = L.shadow;
    return el;
  }
  function rnd(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function grain(root, tl, o) {
    const g = Number(val(o.V, "grain")) / 100;
    // (2026-10-27: a see-through graphic over a video - its own backdrop off - drew this grey noise over the whole
    // frame at 20 %: a grey veil on the footage. Over a video the grain is the footage's own, on the graphic only -
    // compose.py's "match")
    if (!(g > 0) || (o.V && (o.V.background === false || o.V.background === "false"))) return null;
    const N = 192, cv = document.createElement("canvas"); cv.width = cv.height = N;
    const ctx = cv.getContext("2d"), im = ctx.createImageData(N, N), r = rnd(o.seed || 7);
    for (let i = 0; i < N * N; i++) { const v = 128 + (r() + r() + r() - 1.5) * 150; im.data.set([v, v, v, 255], i * 4); }
    ctx.putImageData(im, 0, 0);
    const el = document.createElement("div"); el.className = "ml-grain";
    el.style.backgroundImage = `url(${cv.toDataURL()})`;
    el.style.backgroundSize = `${Math.round(N * Math.max(1, o.U || 1))}px`;
    el.style.opacity = String(Math.min(1, g * 2.5));
    root.appendChild(el);
    const step = Math.max(1, Math.round((o.fps || 30) / 12)), p = rnd((o.seed || 7) + 1);   // 12 grain frames a second
    for (let f = 0; f < (o.frames || 1); f += step) {
      tl.set(el, {backgroundPosition: `${Math.floor(p() * N)}px ${Math.floor(p() * N)}px`}, o.at ? o.at(f) : f / (o.fps || 30));
    }
    return el;
  }
  // a media slot: the user's picture / video (a file in the graphic's assets\media), else a placeholder in the look
  function media(box, src, o) {
    o = o || {};
    box.classList.add("ml-media");
    if (o.look) box.style.borderRadius = `${o.r !== undefined ? o.r : o.look.radius}px`;
    const fit = o.fit === "contain" ? "contain" : "cover", focus = o.focus || "50% 50%";
    if (src) {
      const isVid = /\.(mp4|mov|webm|m4v)$/i.test(src);
      // a video the lab wrote into the page (looks.media_tags: the only kind HyperFrames plays) - moved into the box
      const tag = isVid && o.slot ? document.querySelector(`video[data-ml-media="${o.slot}"]`) : null;
      if (tag) {
        Object.assign(tag.style, {position: "absolute", inset: "0", width: "100%", height: "100%", objectFit: fit, objectPosition: focus});
        box.appendChild(tag);
        return tag;
      }
      const m = document.createElement(isVid ? "video" : "img");
      m.src = src; m.style.objectFit = fit; m.style.objectPosition = focus;
      if (isVid) {                     // HyperFrames owns playback: a timed, muted clip (never play() / seek here)
        m.muted = true; m.setAttribute("muted", ""); m.setAttribute("playsinline", ""); m.setAttribute("preload", "auto");
        m.id = o.id || ("ml-media-" + Math.floor(rnd(o.seed || 9)() * 1e9)); m.className = "clip";
        m.setAttribute("data-start", String(o.start || 0)); m.setAttribute("data-duration", String(o.duration || 10));
        m.setAttribute("data-track-index", String(o.track || 1));
      }
      box.appendChild(m);
      return m;
    }
    const L = o.look || {}, r = rnd(o.seed || 3), w = box.clientWidth || 400, h = box.clientHeight || 300;
    let a = L.deep || DEF.deep, b = L.paper || DEF.paper, c = L.mustard || DEF.mustard;
    if (o.light) [a, b] = [b, a];                   // a light placeholder (a second scene, say)
    const ang = Math.floor(r() * 360), cx = 20 + r() * 60, cy = 20 + r() * 60;
    box.style.background = `radial-gradient(circle at ${cx}% ${cy}%, ${rgba(c, 0.55)}, transparent 55%), linear-gradient(${ang}deg, ${a}, ${rgba(b, 0.35)})`;
    const t = document.createElement("div");
    Object.assign(t.style, {position: "absolute", left: "8%", bottom: "8%", font: `400 ${Math.max(10, Math.round(Math.min(w, h) * 0.07))}px var(--font-accent)`,
      color: b, opacity: "0.85", letterSpacing: "0.06em", textTransform: "uppercase"});
    t.textContent = o.label || (o.kind === "video" ? "your video" : o.kind === "logo" ? "your logo" : "your photo");
    box.appendChild(t);
    return null;
  }
  // ------------------------------------------------------------------ the effects toolkit (2026-10-19)
  // a proxy tween over [f0, f1] whose onUpdate gets the time in seconds: seek-safe (a render, a snapshot and a live
  // preview all land on the same picture for the same frame)
  function every(tl, o, fn) {
    const fps = o.fps || 30, f0 = o.from || 0, f1 = o.to || o.frames || fps, p = {t: f0 / fps};
    fn(p.t);
    tl.fromTo(p, {t: f0 / fps}, {t: f1 / fps, duration: (f1 - f0) / fps, ease: "none", immediateRender: false,
      onUpdate: () => fn(p.t)}, f0 / fps);
    return p;
  }
  // rich text: *bold* _italic_ ==highlight== ^signal^ inside a text setting -> word spans (class "w") in el;
  // bold = the font's heavier weight when it has one, else its italic (a display serif with one weight).
  // -> {words: [span], marks: [highlight span]}; animate words one by one, marks with MLLook.mark()
  const FONTS = __FONTS__;
  function rich(el, text, o) {
    o = o || {};
    const L = o.look || {}, fam = o.family || "", info = FONTS[fam] || {min: 400, max: 400, italic: false};
    const base = o.weight || 400, heavy = info.max > base ? Math.min(info.max, Math.max(base + 300, 700)) : 0;
    const segs = [], re = /(\*[^*]+\*|_[^_]+_|==[^=]+==|\^[^^]+\^)/g;
    let last = 0, m;
    const s = String(text == null ? "" : text);
    while ((m = re.exec(s))) {
      if (m.index > last) segs.push({t: s.slice(last, m.index)});
      const k = m[0];
      segs.push(k[0] === "*" ? {t: k.slice(1, -1), b: 1} : k[0] === "_" ? {t: k.slice(1, -1), i: 1}
        : k[0] === "=" ? {t: k.slice(2, -2), h: 1} : {t: k.slice(1, -1), c: 1});
      last = m.index + k.length;
    }
    if (last < s.length) segs.push({t: s.slice(last)});
    const words = [], marks = [];
    el.textContent = "";
    segs.forEach(g => g.t.split(/(\s+)/).forEach(w => {
      if (!w) return;
      if (/^\s+$/.test(w)) { el.appendChild(document.createTextNode(" ")); return; }
      const sp = document.createElement("span"); sp.className = "w"; sp.textContent = w;
      sp.style.display = "inline-block";
      if (g.b) { if (heavy) sp.style.fontWeight = String(heavy); else if (info.italic) sp.style.fontStyle = "italic"; else sp.style.color = L.signal || DEF.signal; }
      if (g.i) sp.style.fontStyle = "italic";
      if (g.c) sp.style.color = L.signal || DEF.signal;
      if (g.h) {
        sp.classList.add("ml-hl");
        Object.assign(sp.style, {backgroundImage: `linear-gradient(${rgba(L.mustard || DEF.mustard, 0.85)}, ${rgba(L.mustard || DEF.mustard, 0.85)})`,
          backgroundRepeat: "no-repeat", backgroundPosition: "0 88%", backgroundSize: "100% 42%", padding: "0 0.06em"});
        marks.push(sp);
      }
      el.appendChild(sp); words.push(sp);
    }));
    return {words, marks};
  }
  // a highlighter stroke drawn across a mark (f0..f1, frames), like a marker pen
  function mark(tl, sp, f0, f1, o) {
    const fps = (o && o.fps) || 30;
    tl.set(sp, {backgroundSize: "0% 42%"}, 0);
    tl.fromTo(sp, {backgroundSize: "0% 42%"}, {backgroundSize: "100% 42%", duration: Math.max(0.004, (f1 - f0) / fps), ease: EASE.enter, immediateRender: false}, f0 / fps);
  }
  // handheld camera: a slow, organic wander on a wrapper (its own element - nothing else may tween its x / y /
  // rotation / scale): amount 0-10 (~6 px and 0.25 deg each at 1080 px), overscan so the edges never show;
  // hits = [{f, amount}] = jolts that ring out over ~10 frames (an impact, a beat)
  function handheld(target, tl, o) {
    const A = Number(o.amount || 0), U = o.U || 1, r = rnd(o.seed || 13), hits = o.hits || [], fps = o.fps || 30;
    if (!(A > 0) && !hits.length) return null;
    const ph = Array.from({length: 9}, () => r() * Math.PI * 2);
    const fr = [0.31, 0.73, 1.37], amp = [1, 0.45, 0.2];
    const n = (t, k) => fr.reduce((s, f, j) => s + amp[j] * Math.sin(2 * Math.PI * f * t + ph[k * 3 + j]), 0) / 1.65;
    const scale = 1 + (A * 7 * U) / Math.min(o.W || 1920, o.H || 1080) * 2.2;
    return every(tl, {fps, from: 0, to: o.frames}, t => {
      let x = A * 6 * U * n(t, 0), y = A * 5 * U * n(t, 1), rot = A * 0.06 * n(t, 2);
      hits.forEach(h => { const d = t - h.f / fps; if (d >= 0 && d < 0.6) { const e = Math.exp(-d * 9) * Math.sin(d * 55);
        x += (h.amount || 4) * 5 * U * e; y -= (h.amount || 4) * 7 * U * e; rot += (h.amount || 4) * 0.08 * e; } });
      gsap.set(target, {x, y, rotation: rot, scale, transformOrigin: "50% 50%"});
    });
  }
  // a grid behind for depth: kind "flat" (lines), "dots", or "floor" (a perspective plane running to a horizon);
  // flow = px a second it drifts (the floor moves toward the camera). -> the element (put it first in the scene)
  function grid(parent, tl, o) {
    const U = o.U || 1, W = o.W || 1920, H = o.H || 1080, L = o.look || {}, g = (o.size || 90) * U;
    const c = rgba(o.color || L.ink || DEF.ink, o.alpha != null ? o.alpha : 0.08);
    const wrap = document.createElement("div");
    Object.assign(wrap.style, {position: "absolute", left: "0", top: "0", width: `${W}px`, height: `${H}px`, overflow: "hidden", pointerEvents: "none"});
    const pl = document.createElement("div");
    const lines = o.kind === "dots" ? `radial-gradient(circle, ${c} ${1.6 * U}px, transparent ${1.9 * U}px)`
      : `linear-gradient(${c} ${U}px, transparent ${U}px), linear-gradient(90deg, ${c} ${U}px, transparent ${U}px)`;
    if (o.kind === "floor") {
      wrap.style.perspective = `${H * 0.9}px`; wrap.style.perspectiveOrigin = `50% ${(o.horizon || 0.38) * 100}%`;
      Object.assign(pl.style, {position: "absolute", left: `${-W}px`, top: `${H * (o.horizon || 0.38)}px`, width: `${3 * W}px`, height: `${2.2 * H}px`,
        backgroundImage: lines, backgroundSize: `${g}px ${g}px`, transformOrigin: "50% 0%", transform: "rotateX(78deg)",
        maskImage: "linear-gradient(to bottom, transparent 0%, #000 22%, #000 100%)", webkitMaskImage: "linear-gradient(to bottom, transparent 0%, #000 22%, #000 100%)"});
    } else {
      Object.assign(pl.style, {position: "absolute", left: `${-g}px`, top: `${-g}px`, width: `${W + 2 * g}px`, height: `${H + 2 * g}px`,
        backgroundImage: lines, backgroundSize: `${g}px ${g}px`, backgroundPosition: `${(W / 2) % g}px ${(H / 2) % g}px`,
        maskImage: o.vignette === false ? "none" : "radial-gradient(ellipse at 50% 50%, #000 40%, transparent 85%)",
        webkitMaskImage: o.vignette === false ? "none" : "radial-gradient(ellipse at 50% 50%, #000 40%, transparent 85%)"});
    }
    wrap.appendChild(pl);
    parent.insertBefore(wrap, parent.firstChild);
    if (o.flow && tl) every(tl, {fps: o.fps, from: 0, to: o.frames}, t => { pl.style.backgroundPosition = `0px ${(t * o.flow * U) % g}px`; });
    return wrap;
  }
  // a soft glow in a colour: strength 0-100; kind "box" (a shape), "text", "drop" (an SVG / any outline)
  function glow(el, color, strength, o) {
    const s = Number(strength || 0) / 100, U = (o && o.U) || 1, k = (o && o.kind) || "box";
    if (!(s > 0)) return el;
    const c1 = rgba(color, 0.55 * s), c2 = rgba(color, 0.35 * s), c3 = rgba(color, 0.18 * s);
    if (k === "text") el.style.textShadow = `0 0 ${6 * U}px ${c1}, 0 0 ${18 * U}px ${c2}, 0 0 ${44 * U}px ${c3}`;
    else if (k === "drop") el.style.filter = `drop-shadow(0 0 ${6 * U}px ${c1}) drop-shadow(0 0 ${20 * U}px ${c2})`;
    else el.style.boxShadow = [`0 0 ${8 * U}px ${c1}`, `0 0 ${26 * U}px ${c2}`, `0 0 ${64 * U}px ${c3}`, el.style.boxShadow].filter(x => x && x !== "none").join(", ");
    return el;
  }
  // a liquid fill: the fill (a box whose WIDTH grows - not scaleX, which would squash this) gets a wobbling meniscus
  // at its leading edge and slow bands of light flowing through it. wave = px of the wobble at 1080
  function liquid(fill, tl, o) {
    const U = o.U || 1, L = o.look || {}, col = o.color || L.signal || DEF.signal, h = o.h || fill.clientHeight || 60;
    fill.style.overflow = "visible";
    const sheen = document.createElement("div");
    Object.assign(sheen.style, {position: "absolute", inset: "0", borderRadius: "inherit", overflow: "hidden", pointerEvents: "none",
      backgroundImage: `repeating-linear-gradient(105deg, ${rgba("#ffffff", 0)} 0px, ${rgba("#ffffff", 0.0)} ${40 * U}px, ${rgba("#ffffff", 0.13)} ${80 * U}px, ${rgba("#ffffff", 0)} ${110 * U}px, ${rgba("#ffffff", 0)} ${190 * U}px)`});
    const top = document.createElement("div");                 // a lighter top edge: the surface catching light
    Object.assign(top.style, {position: "absolute", left: "0", right: "0", top: "0", height: "34%", borderRadius: "inherit", pointerEvents: "none",
      background: `linear-gradient(${rgba("#ffffff", 0.28)}, ${rgba("#ffffff", 0)})`});
    const NS = "http://www.w3.org/2000/svg", wv = (o.wave || 10) * U, ww = wv * 2.4;
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("width", ww); svg.setAttribute("height", h); svg.style.position = "absolute"; svg.style.top = "0"; svg.style.right = `${-ww + 1}px`; svg.style.overflow = "visible";
    const path = document.createElementNS(NS, "path"); path.setAttribute("fill", col); svg.appendChild(path);
    fill.appendChild(sheen); fill.appendChild(top); fill.appendChild(svg);
    const N = 14;
    every(tl, {fps: o.fps, from: 0, to: o.frames}, t => {
      sheen.style.backgroundPosition = `${-t * 160 * U}px 0px`;
      let d = `M 0 0`;
      for (let i = 0; i <= N; i++) {
        const y = h * i / N, k = Math.sin(Math.PI * i / N);
        const x = k * (wv * 0.9 + wv * 0.5 * Math.sin(t * 7.0 + i * 0.55) + wv * 0.25 * Math.sin(t * 13.0 - i * 0.9));
        d += ` L ${Math.max(0, x).toFixed(2)} ${y.toFixed(2)}`;
      }
      path.setAttribute("d", d + ` L 0 ${h} Z`);
    });
    return {sheen, svg};
  }
  // a curved sheet: N strips on an arc in 3D, each shaded by the angle it faces the light - reads as a bent page.
  // bend = degrees of arc (0 = flat; animate it with setBend in an onUpdate). -> {el, setBend(deg)}
  function sheet(parent, o) {
    const U = o.U || 1, L = o.look || {}, w = o.w, h = o.h, N = o.strips || 18, col = o.color || L.paper || DEF.paper;
    const r = o.radius != null ? o.radius : 40 * U, light = (o.light != null ? o.light : -35) * Math.PI / 180;
    const el = document.createElement("div");
    Object.assign(el.style, {position: "absolute", left: `${-w / 2}px`, top: `${-h / 2}px`, width: `${w}px`, height: `${h}px`, transformStyle: "preserve-3d"});
    const sw = w / N, strips = [];
    for (let i = 0; i < N; i++) {
      const s = document.createElement("div"), shade = document.createElement("div");
      Object.assign(s.style, {position: "absolute", left: "0", top: "0", width: `${sw + 1.2}px`, height: `${h}px`, background: col,
        transformOrigin: "0 50%", backfaceVisibility: "visible",
        borderRadius: i === 0 ? `${r}px 0 0 ${r}px` : i === N - 1 ? `0 ${r}px ${r}px 0` : "0"});
      Object.assign(shade.style, {position: "absolute", inset: "0", borderRadius: "inherit", background: "#000"});
      s.appendChild(shade); el.appendChild(s); strips.push({s, shade});
    }
    parent.appendChild(el);
    function setBend(deg) {
      const th = Math.max(0.001, Math.abs(deg)) * Math.PI / 180 * Math.sign(deg || 1);
      const chord = Math.abs(th) < 0.002 ? w : 2 * (w / th) * Math.sin(th / 2);
      let x = -chord / 2, z = 0, a = -th / 2;                   // walk the arc strip by strip, edge to edge, centred
      strips.forEach(({s, shade}) => {
        s.style.transform = `translate3d(${x + w / 2}px, 0px, ${z}px) rotateY(${-a * 180 / Math.PI}deg)`;
        const facing = Math.cos(a + th / N / 2 - light);         // 1 = faces the light
        shade.style.opacity = String(Math.max(0, Math.min(0.6, 0.5 - 0.5 * facing + (o.dark || 0))));
        x += sw * Math.cos(a); z += sw * Math.sin(a); a += th / N;
      });
    }                                                           // (the sheet's own transform stays the template's)
    setBend(o.bend || 0);
    return {el, setBend, strips};
  }
  return {EASE, DEF, FONTS, apply, card, grain, media, rnd, rgba, lum, every, rich, mark, handheld, grid, glow, liquid, sheet};
})();
"""


def font_weights() -> dict:
    """{family: {min, max, italic}} of the font library - what rich text's *bold* can use."""
    from . import fonts as FL
    out = {}
    for fam in FL.families():
        ws = [w for f in fam["files"] for w in (f["wght"] if f.get("wght") else (f["weight"], f["weight"]))]
        out[fam["family"]] = {"min": min(ws or [400]), "max": max(ws or [400]),
                              "italic": any(f.get("italic") for f in fam["files"])}
    return out


def js() -> str:
    lk = default()
    return (_JS.replace("__EASE__", json.dumps(motion()))
            .replace("__DEF__", json.dumps(values(lk), ensure_ascii=False))
            .replace("__FB__", json.dumps(FALLBACK))
            .replace("__FONTS__", json.dumps(font_weights(), ensure_ascii=False)))


def ensure(folder: Path) -> bool:
    """A look-aware graphic gets the shared look.css + looks.js in its assets\\looks\\ (rewritten when they changed)
    and its video media slots written into the page (media_tags). -> whether it is look-aware."""
    folder = Path(folder)
    if not is_look_aware(folder):
        return False
    dst = folder / "assets" / "looks"
    dst.mkdir(parents=True, exist_ok=True)
    for name, text in (("look.css", css()), ("looks.js", js())):
        p = dst / name
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
    media_tags(folder)
    return True


VIDEO = (".mp4", ".mov", ".webm", ".m4v")
_MTAG = re.compile(r'\n?<video [^>]*data-ml-media="[^"]*"[^>]*></video>', re.I)


def is_media_setting(d: dict) -> bool:
    """A media slot: a string setting whose id ends in "_media" - a picture or a video file in the graphic's
    assets\\media\\ (the app copies a dropped file there), empty = the template's placeholder."""
    return d.get("type") == "string" and str(d.get("id", "")).endswith("_media")


def media_tags(folder: Path) -> list[str]:
    """HyperFrames plays only the <video> elements written in the page when it compiles it (one made by a script
    stays on its first frame - seen 2026-10-18), so each media slot holding a video gets a timed, muted
    <video data-ml-media="<id>"> right inside the root, the whole length of the graphic; MLLook.media() moves it into
    its box. Slots without a video lose their tag. -> the slots written."""
    from . import overlay_settings as OS
    folder = Path(folder)
    idx = folder / "index.html"
    try:
        decl = OS.declared(folder)
        vals = OS.values(folder) if decl else {}
        c = OS.conf(folder)
    except (ValueError, OSError, KeyError, json.JSONDecodeError):
        return []
    h = idx.read_text(encoding="utf-8")
    new = _MTAG.sub("", h)
    fps, n = float(c["fps"]), int(c["frames"])
    starts = c.get("media_start") or {}              # overlay.json: {slot: frame} - a slot shown from a later frame
    tags = []
    for d in decl:
        v = str(vals.get(d["id"], d.get("default", "")) or "")
        if is_media_setting(d) and v.lower().endswith(VIDEO) and (folder / v).is_file():
            f0 = max(0, min(n - 1, int(starts.get(d["id"], 0))))
            s0 = f"{f0 / fps:.6f}".rstrip("0").rstrip(".") or "0"
            secs = f"{(n - f0) / fps:.6f}".rstrip("0").rstrip(".")
            tags.append(f'<video id="ml-media-{d["id"]}" class="clip" data-ml-media="{d["id"]}" src="{v}" muted '
                        f'playsinline data-start="{s0}" data-duration="{secs}" data-track-index="{len(tags) + 1}"></video>')
    if tags:
        m = re.search(r'<div id="root"[^>]*>', new)
        if m:
            new = new[:m.end()] + "\n" + "\n".join(tags) + new[m.end():]
    if new != h:
        idx.write_text(new, encoding="utf-8")
    return [t.split('data-ml-media="')[1].split('"')[0] for t in tags]


# ------------------------------------------------------------------------------------------- templates' defaults
_DECL = re.compile(r"(<html\b[^>]*?\bdata-composition-variables\s*=\s*')([^']*)(')", re.S | re.I)


def sync_file(index: Path, look: dict | None = None) -> bool:
    """A look-aware template's token settings get the (default) look's values as their defaults. -> changed?"""
    p = Path(index)
    h = p.read_text(encoding="utf-8")
    m = _DECL.search(h)
    if not m:
        return False
    try:
        decl = json.loads(m.group(2))
    except json.JSONDecodeError:
        return False
    v = values(look or default())
    changed = False
    for d in decl:
        if d.get("id") in v and d.get("default") != v[d["id"]]:
            d["default"] = v[d["id"]]
            changed = True
    if not changed:
        return False
    body = "[\n" + ",\n".join("  " + json.dumps(d, ensure_ascii=False) for d in decl) + "\n]"
    p.write_text(h[:m.start(2)] + body + h[m.end(2):], encoding="utf-8")
    return True
