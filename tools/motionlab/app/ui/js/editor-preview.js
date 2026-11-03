/* MotionLab app - js/editor-preview.js: the Editor's helpers and its live preview (EdPreview).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ---- the Editor (0.6.0 step 6; the Mini-editor's buttons until 2026-10-26, the user: "call it just editor ... i mean
// like an actual editor where i can select clips, move them around, trim at my own liking, not just click buttons and
// do it all theoretically ... i want to be able to add sfx to my liking, maybe remove a design and add a template from
// our motion graphics template with the color of my liking, maybe add slow/speed to some clips ... look at open
// source alternative of capcut or premiere or sum and try to implement those in a minimilastic but efficient way"):
// a timeline the way the open-source editors do it - OpenCut / CapCut: the shots on a magnetic main track that always
// closes up, graphics on lanes above it, captions on top, sound effects and the sound below, split at the playhead,
// snapping, a panel to add sounds and templates; Shotcut / Kdenlive: light proxy copies for a smooth preview. Every
// change is a step on the plan (motionlab\miniedit: POST .../miniedit/preview = the timeline as it would be, nothing
// saved); the live preview plays it (`EdPreview`: the clips' light copies, the graphics' own pages, the sounds) - the
// render comes on *Save* = the next version as a job (tools\miniedit.py apply --build). Its own colours (cyan / violet,
// `.ed`), apart from Review's player. Unsaved changes stay in this browser (localStorage) until saved or dropped.
const ED_SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3, 4];
// a clip catalogue line's shot size (motionlab\catalogue.SIZES; 2026-11-03: the shot panel's *What it shows*)
const ED_SIZES = () => [['wide', t('wide|shot')], ['medium', t('medium|shot')], ['close', t('close|shot')], ['detail', t('detail|shot')]];
const ED_CAP_STYLE = ['font', 'weight', 'font_size', 'uppercase', 'first_capital', 'y', 'y_upright'];   // the captions' style first
const ED_ROW = {ruler: 24, seg: 24, cap: 26, gfx: 28, shot: 64, fx: 26, sfx: 30, wave: 40};
// the effects (motionlab\edfx): a chip's name as the engine sends it (English) shown in the page's language; what can
// be added at the playhead, with a line on each; a strength slider's range per kind; the eases in the lab's words
const ED_FX_LABEL = {'Zoom in': t('Zoom in'), 'Zoom out': t('Zoom out'), 'Zoom pulse': t('Zoom pulse'), 'Punch-in': t('Punch-in'), 'Punch-out': t('Punch-out'), 'Tight framing': t('Tight framing'),
  'Shake': t('Shake'), 'Flash': t('Flash'), 'White frame': t('White frame'), 'Black frame': t('Black frame'), 'Stutter': t('Stutter'),
  'Mirror': t('Mirror'), 'Whip': t('Whip'), 'Push': t('Push'), 'Crossfade': t('Crossfade'), 'Overlap': t('Overlap'),
  'RGB split': t('RGB split'), 'Colour flash': t('Colour flash'), 'Light leak': t('Light leak'), 'Dip to black': t('Dip to black'),
  'Dip to white': t('Dip to white'), 'Fade in': t('Fade in'), 'Fade out': t('Fade out'), 'Colour layer': t('Colour layer'),
  'Spotlight': t('Spotlight'), 'Room out of focus': t('Room out of focus'), 'Grey room': t('Grey room'),
  'Pastel room': t('Pastel room'), 'Grid paper room': t('Grid paper room'), 'Painted room': t('Painted room'),
  'Before / after': t('Before / after'), 'Dot reveal': t('Dot reveal'), 'Rabbit hole': t('Rabbit hole'), 'Glitch': t('Glitch'),
  'Corner push': t('Corner push'), 'Into a frame': t('Into a frame'), 'Colour look': t('Colour look'), 'Effect': t('Effect'),
  'Moody look': t('Moody look'), 'Black and white': t('Black and white'), 'Warm look': t('Warm look'), 'Cool look': t('Cool look'),
  'Pop look': t('Pop look'), 'Red film': t('Red film'), 'Soft film': t('Soft film'), 'Lavender look': t('Lavender look')};
const edFxLabel = l => ED_FX_LABEL[l] || l;
// a graphic part of the shot (0.6.1, motionlab\miniedit gfit -> compose's behind / glass / guard / follow)
const ED_FIT = () => [['behind', t('Behind me'), t('Hidden where you are - it sits behind you and moves with the camera')],
  ['glass', t('Frosted glass'), t('The room behind it frosted, with a soft shadow - for cards and pills')],
  ['guard', t('Keep off my face'), t('Never over your face')],
  ['pin', t('Pin to my face'), t('Moves with your face - for labels, arrows, brackets')]];
// the effects the Editor offers (motionlab\edfx ADD; 2026-10-27, the user: "few but higher quality ones" - an older
// edit's other effects keep their chips)
const ED_FX_ADD = () => [['punch_in', t('Punch-in'), t('the shot jumps closer from here')],
  ['lean_in', t('Lean in'), t('a small, quick punch-in on your face for one word')],
  ['slow_push', t('Slow push'), t('a slow, smooth push in - on your face when there is one')],
  ['shake', t('Shake'), t('a short camera shake')], ['flash', t('Flash'), t('a bright flash')],
  ['black_frame', t('Black frame'), t('one black frame')], ['stutter', t('Stutter'), t('a few frames repeat')],
  ['rgb_split', t('RGB split'), t('the colours split apart for a few frames')]];
// what needs a clip's picture (motionlab\edfx CLIP_ONLY): greyed out on a video made of graphics, the stutter on a
// talking video (the picture would leave the voice) - the reason on hover, never an error after the click
const ED_FX_CLIP = new Set(['punch_in', 'lean_in', 'slow_push', 'shake', 'rgb_split', 'stutter']);
const edCap = s => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const ED_FX_RANGE = {zoom: [1.01, 2, 0.01, '×'], punch: [1.01, 2, 0.01, '×'], framing: [1.01, 1.6, 0.01, '×'], shake: [0.004, 0.08, 0.002, ''],
  flash: [0.05, 1, 0.05, ''], room: [0.05, 0.95, 0.05, ''], screen: [0.05, 1, 0.05, '']};
const ED_EASES = () => [['linear', t('Linear')], ['smooth', t('S-curve')], ['in', t('Slow start')], ['out', t('Slow end')],
  ['easy', t('Easy ease')], ['strong', t('Strong ease')], ['glide', t('Glide')]];
// keyframes (motionlab\edkeys; 2026-10-26, CapCut / Premiere / Resolve / OpenCut's way): a selected shot's properties as
// its panel shows them - [prop, label, unit, shown = value x k, a drag's step per pixel (shown units), the plan's
// default] - and the eases of the move after a key
const ED_KEY_PROPS = () => [['zoom', t('Scale'), '%', 100, 0.5, 1], ['x', t('Position X'), 'px', 1, 2, 0], ['y', t('Position Y'), 'px', 1, 2, 0],
  ['rotation', t('Rotation'), '°', 1, 0.5, 0], ['opacity', t('Opacity'), '%', 100, 0.5, 1], ['ax', t('Zoom point X'), '%', 100, 0.25, 0.5],
  ['ay', t('Zoom point Y'), '%', 100, 0.25, 0.5]];
function edKRange(p, S) {
  const W = +S.width || 1920, H = +S.height || 1080;
  return {zoom: [10, 400, 1, 1, 1000], x: [-W, W, 1, -3 * W, 3 * W], y: [-H, H, 1, -3 * H, 3 * H], rotation: [-180, 180, 0.5, -3600, 3600],
    opacity: [0, 100, 1, 0, 100], ax: [0, 100, 1, 0, 100], ay: [0, 100, 1, 0, 100]}[p] || [0, 100, 1, 0, 100];
}
const ED_KEY_EASES = () => [['linear', t('Linear')], ['in', t('Ease in')], ['out', t('Ease out')], ['smooth', t('Ease in and out')],
  ['easy', t('Easy ease')], ['strong', t('Strong ease')], ['glide', t('Glide')], ['launch', t('Launch')], ['hold', t('Hold')], ['pop', t('Pop')]];
const ED_EASE_TIP = () => ({linear: t('The same speed all the way'), in: t('Starts slowly, ends fast'), out: t('Starts fast, ends slowly'),
  smooth: t('Slow start and slow end'), easy: t("A gentle start and end - After Effects' Easy Ease"),
  strong: t('Slow away, quick through the middle, a slow landing'), glide: t('Off at once, then a long soft landing - punch-ins and pushes'),
  launch: t('A long wind-up, then away - exits'), hold: t('Stays put, then jumps at the next key'), pop: t('Overshoots a little and settles')});
const ED_KEY_MAP = {zoom: 'zoom', x: 'dx', y: 'dy', rotation: 'rotation', opacity: 'opacity'};
const edKSpec = (d, p) => (p === 'ax' || p === 'ay' ? (d.anchor || [])[p === 'ax' ? 0 : 1] : d[ED_KEY_MAP[p]]);
const edKKeys = (d, p) => { const v = edKSpec(d, p); return v && typeof v === 'object' && Array.isArray(v.keys) && v.keys.length ? v.keys : null; };
function edKSet(d, p, v) { if (p === 'ax' || p === 'ay') { const a = [...(d.anchor || [0.5, 0.5])]; a[p === 'ax' ? 0 : 1] = v; d.anchor = a; } else d[ED_KEY_MAP[p]] = v; }
// transitions (motionlab\edtrans): a sign per kind, its name as the engine sends it (English) in the page's language, a
// line on each, the directions of a slide / whip
const ED_TR_ICON = {mix: '◐', black: '●', white: '○', flash: '✦', zoom_in: '⊕', zoom_out: '⊖', slide: '⇆', whip: '≫', spin: '↻', glitch: '▚', leak: '☀'};
const ED_TR_LABEL = {'Mix': t('Mix'), 'Dip to black': t('Dip to black'), 'Dip to white': t('Dip to white'), 'White flash': t('White flash'),
  'Zoom in': t('Zoom in'), 'Zoom out': t('Zoom out'), 'Slide': t('Slide'), 'Whip': t('Whip'), 'Spin': t('Spin'), 'Glitch': t('Glitch'), 'Light leak': t('Light leak')};
const edTrLabel = l => ED_TR_LABEL[l] || l;
const ED_TR_HOW = () => ({mix: t('one shot fades into the next'), black: t('through black'), white: t('through white'), flash: t('a bright flash on the cut'),
  zoom_in: t('punch in to the cut and out of it'), zoom_out: t('the shot shrinks away, the next one settles'), slide: t('the next shot pushes this one out'),
  whip: t('a fast whip pan'), spin: t('a spin out and back in'), glitch: t('a glitchy jump with a colour split'), leak: t('a mix with a warm light leak')});
const ED_DIRS = () => [['left', '←', t('Left')], ['right', '→', t('Right')], ['up', '↑', t('Up')], ['down', '↓', t('Down')]];
const ED_SNAP_PX = 8;
const ED_KIND = {whoosh: t('Whoosh'), whip: t('Whip'), riser: t('Riser'), air: t('Air'), click: t('Click'), key: t('Keys'),
  pop: t('Pop'), chime: t('Chime'), impact: t('Impact'), thump: t('Thump'), zap: t('Zap'), ching: t('Ching'), chip: t('Chip'),
  chip_hit: t('Chip hit'), crackle: t('Crackle'), lighter: t('Lighter'), tick: t('Tick'), shimmer: t('Shimmer'), buzz: t('Buzz'),
  cork: t('Cork'), flutter: t('Flutter'), ghost: t('Ghost'), shutter: t('Shutter')};
const edKind = k => ED_KIND[k] || k;
// a recorded sound effect for the preview: through the Editor's route - Edge never answered a script's fetch of an
// address ending in .wav (2026-10-26; an <audio> plays it), and the route serves this PC's library sounds only
const edSoundUrl = file => `/api/editor/sound?file=${encodeURIComponent(file)}`;
const meHue = k => [...String(k)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);     // a sound kind's colour
const ED_EASE = {hold: () => 0, linear: x => x, smooth: x => x * x * (3 - 2 * x), in: x => x * x, out: x => 1 - (1 - x) * (1 - x),
  in3: x => x * x * x, out3: x => 1 - (1 - x) ** 3, pop: x => 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2};
// 2026-10-27 (the user: "ease-in ease-out stuff ... basic flow keyframe charts"): compose's BEZIERS + a key's own curve
// "cubic(x1,y1,x2,y2)" (the chart's two handles); the eases that are no Bezier start the chart from a look-alike
const ED_BEZ = {easy: [0.33, 0, 0.67, 1], strong: [0.7, 0, 0.3, 1], glide: [0.16, 1, 0.3, 1], launch: [0.7, 0, 0.84, 0]};
const ED_BEZ_LIKE = {linear: [0, 0, 1, 1], smooth: [0.42, 0, 0.58, 1], in: [0.55, 0.085, 0.68, 0.53], out: [0.25, 0.46, 0.45, 0.94],
  pop: [0.34, 1.56, 0.64, 1], in3: [0.55, 0.055, 0.675, 0.19], out3: [0.215, 0.61, 0.355, 1]};
const edBezTab = {};
function edBezier(b) {
  const key = b.join(',');
  if (edBezTab[key]) return edBezTab[key];
  const [x1, y1, x2, y2] = b, N = 256, M = 1024, xs = [], ys = [], tab = [];
  for (let i = 0; i <= M; i++) { const s = i / M, u = 1 - s; xs.push(3 * u * u * s * x1 + 3 * u * s * s * x2 + s ** 3); ys.push(3 * u * u * s * y1 + 3 * u * s * s * y2 + s ** 3); }
  for (let i = 0, j = 0; i <= N; i++) {
    const x = i / N;
    while (j < M - 1 && xs[j + 1] < x) j++;
    const r = xs[j + 1] > xs[j] ? clamp((x - xs[j]) / (xs[j + 1] - xs[j]), 0, 1) : 0;
    tab.push(ys[j] + (ys[j + 1] - ys[j]) * r);
  }
  return (edBezTab[key] = x => { const p = clamp(x, 0, 1) * N, i = Math.min(N - 1, Math.floor(p)); return tab[i] + (tab[i + 1] - tab[i]) * (p - i); });
}
function edBezOf(e) {
  if (ED_BEZ[e]) return ED_BEZ[e];
  if (typeof e !== 'string' || !e.startsWith('cubic(') || !e.endsWith(')')) return null;
  const b = e.slice(6, -1).split(',').map(Number);
  return b.length === 4 && b.every(Number.isFinite) ? [clamp(b[0], 0, 1), b[1], clamp(b[2], 0, 1), b[3]] : null;
}
const edEaseFn = e => ED_EASE[e] || (edBezOf(e) ? edBezier(edBezOf(e)) : ED_EASE.linear);
// a curve as a little picture (an ease tile) or the chart: time left to right, the value bottom to top (0..1 in the box,
// an overshoot above it)
function edEasePath(e, w, h) {
  const fn = edEaseFn(e), pts = [];
  for (let i = 0; i <= 40; i++) { const x = i / 40, v = e === 'hold' ? (i < 40 ? 0 : 1) : fn(x); pts.push(`${(x * w).toFixed(1)},${(h - v * h).toFixed(1)}`); }
  return `M${pts.join(' L')}`;
}
const edEaseIcon = e => `<svg class="edeico" viewBox="-3 -7 40 34" width="40" height="34" aria-hidden="true"><path d="M0 24 L34 24 M0 24 L0 0" class="edeax"/><path d="${edEasePath(e, 34, 24)}" class="edecv"/></svg>`;
// a plan's animated value (motionlab\compose Curve): a number, {keys: [[f, v, ease]]}, {start, values}, "@name"
function edCurve(spec, named, dflt) {
  if (typeof spec === 'string' && spec[0] === '@') spec = (named || {})[spec.slice(1)];
  if (spec == null) return () => dflt;
  if (typeof spec === 'number') return () => spec;
  const sc = spec.scale ?? 1, of = spec.offset ?? 0;
  if (spec.keys && spec.keys.length) {
    const ks = [...spec.keys].sort((a, b) => a[0] - b[0]);
    return f => {
      let v;
      if (f <= ks[0][0]) v = ks[0][1];
      else if (f >= ks[ks.length - 1][0]) v = ks[ks.length - 1][1];
      else { let i = 0; while (ks[i + 1][0] <= f) i++; const x = (f - ks[i][0]) / Math.max(1e-9, ks[i + 1][0] - ks[i][0]);
        v = ks[i][1] + (ks[i + 1][1] - ks[i][1]) * edEaseFn(ks[i][2] || 'linear')(x); }
      return v * sc + of;
    };
  }
  if (spec.values) return f => spec.values[clamp(Math.round(f) - spec.start, 0, spec.values.length - 1)] * sc + of;
  return () => dflt;
}
// the clip frame a clip layer shows at timeline frame f (its jumps, speed, a held frame - compose ClipLayer.src_index)
function edSrcAt(L, f) {
  const J = (L.jumps && L.jumps.length ? L.jumps : [[L.start, L.in]]).map(j => [+j[0], +j[1]]).sort((a, b) => a[0] - b[0]);
  let j = J[0];
  for (const x of J) if (x[0] <= f) j = x;
  return L.hold ? j[1] : j[1] + Math.floor((f - j[0]) * (L.speed || 1) + 1e-6);
}
// the captions as this edit has them, in the graphic's own page before it is saved (E = the state's capedits for its
// folder: {cues: the whole list the engine made - new words, other frames, split, added, removed})
const edCapPatch = E => `(function(){var C=window.CAPTIONS;if(!C)return;C.cues=${JSON.stringify((E.cues || []).map(c => ({f0: c.f0, f1: c.f1, words: c.words}))).replace(/</g, '\\u003c')};})();`;

// ---- the live preview: the edit played from its parts, no render
function edVolume(v) {                                         // the preview's listening level, 0..1 (localStorage)
  try {
    if (v !== undefined) { localStorage.setItem('ml.editor.vol', String(v)); return v; }
    const x = parseFloat(localStorage.getItem('ml.editor.vol')); return isFinite(x) ? clamp(x, 0, 1) : 0.8;
  } catch (e) { return v === undefined ? 0.8 : v; }
}
// the platforms' safe zones over the preview of an upright video (motionlab\safezones - the state's "safe"): where
// TikTok / Reels / Shorts draw their own tabs, name + caption and buttons; this viewer's choice (localStorage)
const ED_SAFE_WORDS = () => ({top: t('Tabs and search'), bottom: t('Name, caption and sound'), 'right rail': t('Like, comment, share')});
function edSafeK(v) {
  try { if (v !== undefined) { localStorage.setItem('ml.editor.safe', v); return v; } const x = localStorage.getItem('ml.editor.safe'); return x == null ? 'all' : x; }
  catch (e) { return v === undefined ? 'all' : v; }
}
function edPvH(v) {                                            // the preview's height the user dragged (px), or null
  try {
    if (v !== undefined) { if (v == null) localStorage.removeItem('ml.editor.pvh'); else localStorage.setItem('ml.editor.pvh', String(Math.round(v))); return v; }
    const x = parseFloat(localStorage.getItem('ml.editor.pvh')); return isFinite(x) ? x : null;
  } catch (e) { return null; }
}
// the panel's sections (<details data-sec>) open or closed as the user left them - this viewer's own
function edSecs() { try { return JSON.parse(localStorage.getItem('ml.editor.secs') || '{}') || {}; } catch (e) { return {}; } }
function edSecSet(k, open) { const m = edSecs(); m[k] = !!open; try { localStorage.setItem('ml.editor.secs', JSON.stringify(m)); } catch (e) { /* private window */ } }
const edDigits = step => (String(step).split('.')[1] || '').length;
// a number as the editors show one (Premiere's Properties panel, CapCut's inspector, OpenCut's): its name - drag it
// left or right (Shift = finer) -, a slider, the number to type (up / down = one step, Shift = ten) with its unit, and
// ↺ back to its default. While dragged it shows live (o.live); let go = one change (o.commit). o.after = more controls
// in the row (a keyframe's diamond, Mute); o.reset = what ↺ does instead of the default, o.changed = when it shows.
function edNum(o) {
  const v = +o.value, dg = edDigits(o.step), changed = o.changed ?? (o.dflt != null && Math.abs(v - o.dflt) > 1e-9);
  return `<div class="ednum${o.cls ? ' ' + o.cls : ''}${o.disabled ? ' off' : ''}" data-num="${esc(o.id)}"${o.tip ? ` title="${esc(o.tip)}"` : ''}>
    <span class="ednl" title="${ta('Drag left or right to change it')}">${esc(o.label)}</span>
    <input type="range" class="ednr" min="${o.min}" max="${o.max}" step="${o.step}" value="${clamp(v, o.min, o.max)}"${o.disabled ? ' disabled' : ''} aria-label="${esc(o.label)}" tabindex="-1">
    <span class="ednb"><input type="number" class="ednv" step="${o.step}" value="${+v.toFixed(dg)}" data-fid="num:${esc(o.id)}"${o.disabled ? ' disabled' : ''} aria-label="${esc(o.label)}"><span class="ednu">${esc(o.unit || '')}</span></span>
    ${o.after || ''}<button type="button" class="ednreset"${changed && !o.disabled ? '' : ' hidden'} title="${ta('Back to how it was')}">↺</button></div>`;
}
function edNumBind(root, o) {
  const r = $(`[data-num="${CSS.escape(o.id)}"]`, root);
  if (!r) return;
  const rg = $('.ednr', r), nb = $('.ednv', r), lb = $('.ednl', r), rs = $('.ednreset', r), dg = edDigits(o.step);
  const lo = o.hardMin ?? o.min, hi = o.hardMax ?? o.max;
  const fix = v => +clamp(Math.round(v / o.step) * o.step, lo, hi).toFixed(dg);
  let v0 = +nb.value, timer = 0;
  const show = v => { nb.value = v; rg.value = clamp(v, o.min, o.max); };
  const live = v => { show(v); if (o.live) o.live(v); };
  const back = () => { show(v0); if (o.revert) o.revert(); else if (o.live) o.live(v0); };
  const done = v => { clearTimeout(timer); timer = 0; v = fix(v); if (Math.abs(v - v0) < 1e-9) return back(); v0 = v; show(v); o.commit(v); };
  rg.oninput = () => live(fix(+rg.value));
  rg.onchange = () => done(+rg.value);
  nb.onchange = () => { const v = +nb.value; if (nb.value !== '' && Number.isFinite(v)) done(v); else back(); };
  const nudge = (dir, big) => { const v = fix(+nb.value + dir * o.step * (big ? 10 : 1)); live(v); clearTimeout(timer); timer = setTimeout(() => done(v), 500); };
  nb.onfocus = () => nb.select();                            // (a click: type over it)
  nb.addEventListener('wheel', e => { if (document.activeElement !== nb) return;   // only while it has the focus (Kdenlive):
    e.preventDefault(); nudge(e.deltaY < 0 ? 1 : -1, e.shiftKey); }, {passive: false});   // scrolling the panel never changes it
  nb.onkeydown = e => {
    if (e.key === 'Enter') { e.preventDefault(); nb.blur(); }
    else if (e.key === 'Escape') { e.preventDefault(); clearTimeout(timer); back(); nb.blur(); }
    else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); nudge(e.key === 'ArrowUp' ? 1 : -1, e.shiftKey); }
  };
  lb.onpointerdown = e => {
    if (nb.disabled || e.button) return;
    e.preventDefault(); lb.setPointerCapture(e.pointerId);    // (captured: the drag goes on outside the panel)
    const x0 = e.clientX, s0 = +nb.value, per = (o.max - o.min) / 240;   // (the slider's whole range over 240 px)
    let v = s0, moved = false;
    lb.classList.add('drag');
    lb.onpointermove = ev => { if (ev.clientX === x0 && !moved) return;
      moved = true; v = fix(s0 + (ev.clientX - x0) * per * (ev.shiftKey ? 0.1 : 1)); live(v); };
    lb.onpointerup = lb.onpointercancel = () => { lb.onpointermove = lb.onpointerup = lb.onpointercancel = null; lb.classList.remove('drag');
      if (moved) done(v); };
  };
  if (rs) rs.onclick = () => { if (o.reset) o.reset(); else done(o.dflt); };
}
// 0.6.1 (vertical framing, step 5): a shot's Framing section - a horizontal clip in a vertical video (motionlab\reframe):
// the layout, a still crop or one that follows; the crop itself dragged on the preview (EdPreview.cropDown)
const ED_FRAMES = () => [['auto', t('Auto'), t('MotionLab picks the framing of each shot')],
  ['fill', t('Fill'), t('The face fills the frame')], ['fit', t('Fit'), t('All of the picture in a band across the middle')],
  ['split', t('Split'), t('Two people, one above the other')], ['screen', t('Screen'), t('The screen on top, the face camera below')],
  ['game', t('Game'), t('The face camera on top, the game below')]];
function edFrameIcon(k) {
  const head = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r}"/>`;
  const inner = {auto: '<text x="11" y="21" text-anchor="middle">A</text>', fill: `${head(11, 14, 4)}<path d="M4 31 Q11 19 18 31"/>`,
    fit: `<rect x="2" y="11" width="18" height="12" rx="1" class="f"/>${head(11, 16, 2.5)}`,
    split: `<path d="M2 17 H20"/>${head(11, 9.5, 3)}${head(11, 25, 3)}`,
    screen: `<rect x="2" y="2" width="18" height="15" class="f"/><path d="M5 7 H15 M5 11 H12"/>${head(11, 25, 3.5)}`,
    game: `${head(11, 7, 3)}<path d="M2 12 H20"/><rect x="5" y="20" width="12" height="7" rx="3.5"/>`}[k] || '';
  return `<svg class="edfri" viewBox="0 0 22 34" aria-hidden="true"><rect x="1" y="1" width="20" height="32" rx="3.5"/>${inner}</svg>`;
}
function edFrameSec(s) {
  const fr = s.frame;
  if (!fr) return '';
  const mine = fr.by === 'user';
  return `<details class="edsec" data-sec="shot.frame" open><summary>${t('Framing')}${mine ? ` <span class="edmine">${t('yours')}</span>` : ''}</summary>
    <div class="edframes">${ED_FRAMES().map(([k, l, tip]) => {
      const on = k === 'auto' ? !mine : mine && fr.layout === k, now = !mine && fr.by && fr.layout === k;
      return `<button class="edframe${on ? ' on' : ''}${now ? ' now' : ''}" data-frame="${k}" data-name="${esc(l)}" title="${esc(tip)}${now ? ` · ${esc(t('what Auto picked'))}` : ''}"${fr.shake ? ' disabled' : ''}>${edFrameIcon(k)}<span>${esc(l)}</span></button>`; }).join('')}</div>
    <div class="edchips">${[['hold', t('Still')], ['follow', t('Follow')]].map(([m, l]) => `<button data-fmode="${m}" class="${fr.mode === m ? 'on' : ''}"${fr.shake ? ' disabled' : ''}>${l}</button>`).join('')}</div>
    <div class="small muted">${fr.shake ? t('This shot shakes - remove its shake to change its framing.') : t('Drag the picture in the preview to move its crop.')}</div></details>`;
}

class EdPreview {
  constructor(box, o) {
    this.box = box; this.fps = o.fps; this.W = o.W; this.H = o.H; this.media = o.media || {}; this.onFrame = o.onFrame || (() => {});
    this.onPlay = o.onPlay || (() => {});
    box.innerHTML = `<div class="edstage"><div class="edlayers"></div><div class="edwait" hidden></div></div>`;
    this.stage = $('.edstage', box); this.layers = $('.edlayers', box); this.waitEl = $('.edwait', box);
    this.pool = {}; this.frames = new Map(); this.solids = new Map(); this.html = new Map(); this.buf = new Map();
    this.f = 0; this.playing = false; this.raf = 0; this.sched = []; this.capEdits = {}; this.activeIds = new Set(); this.muted = false;
    this.vol = edVolume();                                       // the listening level (the volume slider; never saved into the video)
    this.dragFor = o.dragFor || null; this.onCrop = o.onCrop || null;   // (0.6.1: the shot whose crop a drag moves; where to)
    this.stage.addEventListener('pointerdown', e => this.cropDown(e));
    this.stage.addEventListener('click', () => { if (this.noClick) { this.noClick = false; return; } if (this.playing) this.pause(); else this.play(); });
    this.ro = new ResizeObserver(() => this.fit()); this.ro.observe(box);
    this.fit();
  }
  wait(html) { this.waitEl.hidden = !html; this.waitEl.innerHTML = html || ''; }
  // 0.6.1 (vertical framing, step 5): the selected shot's crop dragged on the preview - the picture follows the pointer
  // (this.over, drawn by views()), its new centre (shares of its clip, in the panel under the pointer) to onCrop on
  // release; a press that does not move stays a click (play / pause)
  cropDown(e) {
    this.noClick = false;
    const id = e.button === 0 && this.S && this.dragFor && !this.playing ? this.dragFor(this.f) : null;
    const d0 = id && this.S.draw.find(d => d.t === 'clip' && d.id === id && d.start <= this.f && this.f <= d.end);
    if (!d0) return;
    const r = this.stage.getBoundingClientRect(), X = (e.clientX - r.left) / this.sc, Y = (e.clientY - r.top) / this.sc;
    const v = this.views(d0).filter(x => !x.bg).reverse().find(x => { const q = x.rect || [0, 0, this.W, this.H];
      return X >= q[0] && X <= q[0] + q[2] && Y >= q[1] && Y <= q[1] + q[3]; });
    const g = v && ((this.pool[v.src] || []).find(x => x.layer === v.id) || {}).geo;
    if (!g) return;
    const x0 = e.clientX, y0 = e.clientY, lo = u => u / (2 * g.zm);
    let moved = false, nx = g.cx, ny = null;
    this.stage.setPointerCapture(e.pointerId);
    const mv = ev => {
      if (!moved && Math.abs(ev.clientX - x0) + Math.abs(ev.clientY - y0) < 4) return;
      moved = true;
      nx = clamp(g.cx - (ev.clientX - x0) * (d0.mirror ? -1 : 1) / (g.pw * g.zm), lo(g.ux), 1 - lo(g.ux));
      ny = g.uy / g.zm < 0.999 ? clamp(g.cy - (ev.clientY - y0) / (g.ph * g.zm), lo(g.uy), 1 - lo(g.uy)) : null;   // (room down too: zoomed in)
      this.over = {id, k: v.pk || 0, x: nx, y: ny};
      this.render(this.f);
    };
    const up = () => {
      ['pointermove', 'pointerup', 'pointercancel'].forEach((t_, i) => this.stage.removeEventListener(t_, i ? up : mv));
      if (!moved) return;
      this.noClick = true;
      if (this.onCrop) this.onCrop({shot: id, panel: v.pk || 0, x: nx, y: ny});
    };
    this.stage.addEventListener('pointermove', mv); this.stage.addEventListener('pointerup', up); this.stage.addEventListener('pointercancel', up);
  }
  setSafe(z) { this.safe = z || null; this.drawSafe(); }
  drawSafe() {
    if (!this.safe) { if (this.safeEl) this.safeEl.hidden = true; return; }
    if (!this.safeEl) { this.safeEl = document.createElement('div'); this.safeEl.className = 'edsafe'; this.stage.appendChild(this.safeEl); }
    const s = this.sc || 1, w = ED_SAFE_WORDS(), box = ([x0, y0, x1, y1]) => `left:${x0 * s}px;top:${y0 * s}px;width:${(x1 - x0) * s}px;height:${(y1 - y0) * s}px`;
    this.safeEl.hidden = false;
    this.safeEl.innerHTML = Object.entries(this.safe.bands).map(([k, b]) => `<i class="edsb ${k === 'right rail' ? 'rail' : k}" style="${box(b)}"><span>${esc(w[k] || k)}</span></i>`).join('')
      + `<b class="edsr" style="${box(this.safe.safe)}"></b>`;
  }
  fit(soft = false) {
    // (as high as the window leaves once the whole timeline is in sight - or as the user dragged it with the handle)
    const bw = Math.max(200, this.box.clientWidth || 400), tl = document.getElementById('edtl'), tr = this.box.parentElement && $('.edtrans', this.box.parentElement);
    const top = this.box.getBoundingClientRect().top + (($('main') || {}).scrollTop || 0);
    const auto = window.innerHeight - top - (tr ? tr.offsetHeight + 14 : 54) - (tl ? tl.offsetHeight : 300) - 26;
    const maxH = clamp(edPvH() ?? auto, 200, Math.max(240, window.innerHeight - 220));
    const sc = Math.min(bw / this.W, maxH / this.H);
    if (soft && this.sc && Math.abs(sc - this.sc) * this.H < 4) return;
    this.sc = sc;
    if (this.safe) this.drawSafe();
    this.stage.style.width = `${Math.round(this.W * this.sc)}px`; this.stage.style.height = `${Math.round(this.H * this.sc)}px`;
    if (this.S) this.render(this.f, true);
  }
  setState(S, capEdits) {
    this.S = S; this.N = S.frames; this.capEdits = capEdits || {}; this.over = null;
    this.g = Object.fromEntries(S.graphics.map(g => [g.id, g]));
    const live = new Set(S.graphics.map(g => this.gkey(g)));
    for (const [k, F] of this.frames) if (!live.has(k)) { F.wrap.remove(); this.frames.delete(k); }
    this.shotIds = new Set(S.shots.map(s => s.id));
    this.clips = S.draw.filter(d => d.t === 'clip');
    this.voice = S.sound === 'follows';
    const want = S.song || S.audio_file;                       // the song (or a sound made some other way) under it
    if (want && (!this.songEl || this.songEl.dataset.src !== want)) {
      if (!this.songEl) { this.songEl = document.createElement('audio'); this.songEl.preload = 'auto'; this.box.appendChild(this.songEl); }
      this.songEl.dataset.src = want; this.songEl.src = fileUrl(want);
    }
    this.songAt = S.song ? (S.song_cut || {}).start_s || 0 : 0;      // (seconds into the song where the video starts)
    if (this.songEl) { this.songEl.volume = this.vol * Math.min(1, Math.pow(10, ((S.song && S.song_cut) || {db: 0}).db / 20));
      if (this.playing && !this.muted) this.songEl.currentTime = this.f / this.fps + this.songAt; }
    if (!S.audio_file) S.sfx.forEach(q => this.buffer(this.sfxUrl(q)));       // (a fixed sound has its effects in it)
    if (this.f > this.N - 1) this.f = Math.max(0, this.N - 1);
    if (this.playing) { this.unschedule(); this.schedule(this.f); }
    this.render(this.f, true);
  }
  // clips: two light copies per clip (the one showing, the next one waiting on its first frame), never moved in the page
  elFor(L) {
    const P = this.pool[L.src] || (this.pool[L.src] = []);
    let e = P.find(x => x.layer === L.id);
    if (e) return e;
    e = P.find(x => !x.layer || (!this.activeIds.has(x.layer) && x.layer !== this.preId));
    if (!e && P.length < 8) { e = this.makeEl(L.src); P.push(e); }     // (a transition shows a clip up to three times, a layout's panels too)
    if (e) { e.layer = L.id; e.at = null; }
    return e;
  }
  makeEl(src) {
    const m = this.media[src] || {}, wrap = document.createElement('div');
    wrap.className = 'edclip'; wrap.hidden = true;
    let v;
    if (m.photo) { v = document.createElement('img'); v.src = `/api/thumb?video=${encodeURIComponent(m.photo)}&f=0&fps=${this.fps}`; v.alt = ''; }
    else { v = document.createElement('video'); v.preload = 'auto'; v.playsInline = true; v.muted = true; v.src = fileUrl(m.proxy || m.source || ''); }
    // (its crop needs its own size: placed before it is known, a paused preview stayed wrong - 2026-10-29)
    v.addEventListener(m.photo ? 'load' : 'loadedmetadata', () => { if (this.S && !this.dead) this.render(this.f); });
    wrap.appendChild(v); this.layers.appendChild(wrap);
    return {wrap, v, layer: null, photo: !!m.photo};
  }
  box4(rect) { const r = rect || [0, 0, this.W, this.H], s = this.sc; return [r[0] * s, r[1] * s, r[2] * s, r[3] * s]; }
  // 0.6.1 (a vertical layout, motionlab\reframe.py): the clip once per panel - the first one keeps its id (its sound,
  // its zoom point), the others their own crop centre (+ a shake's swing) - over its backdrop, as compose draws it
  // (a zoom under 1 shrinks each panel here, the whole layout there)
  views(d) {
    const o = this.over && this.over.id === d.id ? this.over : null;        // (a crop being dragged: its point now)
    const at = (a, k) => (o && o.k === k ? [o.x, o.y == null ? (a || [0.5, 0.5])[1] : o.y] : a);
    if (!d.panels || !d.panels.length) return [o ? {...d, anchor: at(d.anchor, 0), face: null} : d];
    const out = d.backdrop ? [{...d, id: d.id + '#bg', panels: null, zoom: 1, anchor: [0.5, 0.5], face: null, bg: d.backdrop}] : [];
    d.panels.forEach((p, k) => out.push({...d, id: k ? `${d.id}#p${k}` : d.id, panels: null, rect: p.rect, pz: p.zoom, pk: k,
      anchor: k ? d.anchor : at(d.anchor, 0), own: k ? at(p.anchor || [0.5, 0.5], k) : null}));
    return out;
  }
  placeClip(e, d, z, f) {
    const [x, y, w, h] = this.box4(d.rect), C = this.S.curves, s = this.sc;
    const st = e.wrap.style;
    st.left = `${x}px`; st.top = `${y}px`; st.width = `${w}px`; st.height = `${h}px`; st.zIndex = z;
    st.opacity = clamp(edCurve(d.opacity, C, 1)(f), 0, 1);
    const zm = edCurve(d.zoom, C, 1)(f) * (d.pz != null ? Math.max(1, edCurve(d.pz, C, 1)(f)) : 1), an = d.anchor || [0.5, 0.5];
    let ax = edCurve(an[0], C, 0.5)(f), ay = edCurve(an[1], C, 0.5)(f);
    const dx = edCurve(d.dx, C, 0)(f) * s, dy = edCurve(d.dy, C, 0)(f) * s, rot = edCurve(d.rotation, C, 0)(f);
    const fc = d.face && d.face.values[clamp(f - d.face.start, 0, d.face.values.length - 1)];
    const sw = (a, v) => (a && Array.isArray(a.values) && a.values.length && f >= a.start && f < a.start + a.values.length ? v - a.values[a.values.length - 1] : 0);
    if (d.own) { ax = edCurve(d.own[0], C, 0.5)(f) + sw(an[0], ax); ay = edCurve(d.own[1], C, 0.5)(f) + sw(an[1], ay); }
    else if (fc) {                // compose zoom_point: on the face, a shake's swing (round its resting value) added
      ax = fc[0] + sw(an[0], ax); ay = fc[1] + sw(an[1], ay);
    }
    const contain = d.fit === 'contain';
    e.v.style.objectFit = contain ? 'contain' : 'cover';
    // (compose: x / y move the clip's box, a rotation turns the box round its centre; zoomed in, the zoom point is the
    // crop's centre - kept inside the picture - so the picture moves as well as scales; under 1 the box shrinks round it)
    st.transform = dx || dy || rot ? `translate(${dx}px, ${dy}px)${rot ? ` rotate(${rot}deg)` : ''}` : '';
    const vw = e.v.videoWidth || e.v.naturalWidth || w, vh = e.v.videoHeight || e.v.naturalHeight || h;
    const k = contain ? Math.min(w / vw, h / vh) : Math.max(w / vw, h / vh), pw = vw * k, ph = vh * k;
    const ux = contain ? 1 : w / pw, uy = contain ? 1 : h / ph;
    // (cover: the element holds only the part of the picture its box shows - a horizontal clip in a vertical video, 32 %
    // of it - so object-position puts that part on the crop's centre and the transform makes only the zoom's own move;
    // 2026-10-29: before, the middle was shown, moved - wrong for any crop off the middle)
    const wx = clamp(ax, ux / 2, 1 - ux / 2), wy = clamp(ay, uy / 2, 1 - uy / 2);
    e.v.style.objectPosition = contain ? '50% 50%' : `${ux < 1 ? (wx - ux / 2) / (1 - ux) * 100 : 50}% ${uy < 1 ? (wy - uy / 2) / (1 - uy) * 100 : 50}%`;
    if (zm >= 1) {
      const cx = clamp(ax, ux / (2 * zm), 1 - ux / (2 * zm)), cy = clamp(ay, uy / (2 * zm), 1 - uy / (2 * zm));
      const bx = contain ? 0.5 : wx, by = contain ? 0.5 : wy;
      e.v.style.transformOrigin = '50% 50%';
      e.v.style.transform = `translate(${(d.mirror ? -1 : 1) * (bx - cx) * pw * zm}px, ${(by - cy) * ph * zm}px) scale(${zm})${d.mirror ? ' scaleX(-1)' : ''}`;
      e.geo = contain ? null : {cx, cy, pw, ph, zm, ux, uy};       // (what a drag of its crop starts from: cropDown)
    } else {
      e.v.style.transformOrigin = `${ax * 100}% ${ay * 100}%`;
      e.v.style.transform = `scale(${zm})${d.mirror ? ' scaleX(-1)' : ''}`;
      e.geo = null;
    }
    st.mixBlendMode = d.blend === 'screen' ? 'screen' : d.blend === 'add' ? 'plus-lighter' : '';
    let fl = 0, flc = '#fff', ex = 0;                        // a flash (over-exposed), a white or a black frame
    if ((d.black || []).includes(f)) { fl = 1; flc = '#000'; }
    else if ((d.flash_white || []).includes(f)) fl = 0.9;
    else if (d.flash_over && d.flash_over[String(f)] != null) { ex = +d.flash_over[String(f)]; fl = 0.25 * ex; }
    // (compose's exposure flash: x (1 + 4k) in linear light = about that to the power 1 / 2.2 here, a little white over)
    // (a backdrop: compose blurs a tenth-size copy by 2.5 px - about 1.3 % of the picture's width - and darkens it)
    const bgw = d.bg === 'blur' ? (e.v.videoWidth || e.v.naturalWidth || w) * Math.max(w / (e.v.videoWidth || e.v.naturalWidth || w), h / (e.v.videoHeight || e.v.naturalHeight || h)) : 0;
    e.v.style.filter = [bgw ? `blur(${(bgw * 25 / 1920).toFixed(1)}px) brightness(0.55)` : '', d.tint ? `url(#${this.tintFilter(d.tint)})` : '', ex ? `brightness(${Math.pow(1 + 4 * ex, 1 / 2.2).toFixed(3)})` : ''].filter(Boolean).join(' ');
    if (fl && !e.fl) { e.fl = document.createElement('i'); e.fl.className = 'edfl'; e.wrap.appendChild(e.fl); }
    if (e.fl) { e.fl.style.background = flc; e.fl.style.opacity = fl; }
  }
  tintFilter(tint) {                                         // a layer's colour multipliers (an RGB split) as an SVG filter
    const id = 'edt' + tint.map(v => Math.round(v * 100)).join('_');
    if (!this.svg) { this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); this.svg.setAttribute('width', '0'); this.svg.setAttribute('height', '0');
      this.svg.style.position = 'absolute'; this.stage.appendChild(this.svg); }
    if (!this.svg.querySelector('#' + id)) this.svg.insertAdjacentHTML('beforeend', `<filter id="${id}" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="${tint[0]} 0 0 0 0 0 ${tint[1]} 0 0 0 0 0 ${tint[2]} 0 0 0 0 0 1 0"/></filter>`);
    return id;
  }
  render(f, seek = false) {
    this.f = f;
    const S = this.S;
    if (!S) return;
    this.stage.classList.toggle('crop', !!(this.dragFor && !this.playing && this.dragFor(f)));   // (its crop can be dragged)
    const fps = this.fps, act = [];
    S.draw.forEach((d, i) => {
      const L = d.t === 'overlay' ? this.g[d.id] : d;
      if (L && L.start <= f && f <= L.end) act.push([d, i]);
    });
    this.activeIds = new Set(act.flatMap(([d]) => d.t === 'clip' ? this.views(d).map(v => v.id) : [d.id]));
    const shown = new Set(), onSol = new Set();
    let main = null, mainDb = 0;
    for (const [d0, i] of act) {
      if (d0.t !== 'clip') continue;
      this.views(d0).forEach((d, k) => {
        if (d.bg && d.bg !== 'blur') {                         // a colour backdrop: a plain box under the panels
          let el = this.solids.get(d.id);
          if (!el) { el = document.createElement('div'); el.className = 'edsolid'; this.layers.appendChild(el); this.solids.set(d.id, el); }
          const [x, y, w, h] = this.box4(d.rect), dx = edCurve(d.dx, S.curves, 0)(f) * this.sc, dy = edCurve(d.dy, S.curves, 0)(f) * this.sc;
          Object.assign(el.style, {left: `${x + dx}px`, top: `${y + dy}px`, width: `${w}px`, height: `${h}px`, zIndex: (i + 1) * 4 + k,
            background: d.bg, opacity: clamp(edCurve(d.opacity, S.curves, 1)(f), 0, 1), mixBlendMode: ''});
          el.hidden = false; onSol.add(d.id);
          return;
        }
        const e = this.elFor(d);
        if (!e) return;
        shown.add(e); this.placeClip(e, d, (i + 1) * 4 + k, f);
        if (this.shotIds.has(d.id)) { main = e; mainDb = (S.shots.find(s => s.id === d.id) || {}).db || 0; }
        if (!e.photo) {
          const want = (edSrcAt(d, f) + 0.5) / fps, v = e.v, rate = d.hold ? 1 : (d.speed || 1);
          if (this.playing && !d.hold && !(d.jumps && d.jumps.length > 1)) {    // (a stutter: shown frame by frame)
            if (v.playbackRate !== rate) v.playbackRate = rate;
            if (v.paused) { if (Math.abs(v.currentTime - want) > 0.5 / fps) v.currentTime = want; v.play().catch(() => {}); }
            else if (Math.abs(v.currentTime - want) > 0.2 * Math.max(1, rate)) v.currentTime = want;
          } else {
            if (!v.paused) v.pause();
            if (seek || Math.abs(v.currentTime - want) > 0.5 / fps) v.currentTime = want;
          }
        }
        e.wrap.hidden = false;
      });
    }
    for (const P of Object.values(this.pool)) for (const e of P) {
      if (!shown.has(e)) { e.wrap.hidden = true; if (!e.photo && !e.v.paused) e.v.pause(); }
      if (!e.photo) { e.v.muted = this.muted || !this.voice || e !== main || (e === main && mainDb <= -60);
        if (e === main) e.v.volume = this.vol * Math.min(1, Math.pow(10, mainDb / 20)); }   // (louder than its own: on save)
    }
    // graphics: each folder's own page in a frame, at its frame
    const onDirs = new Set();
    for (const [d, i] of act) {
      if (d.t !== 'overlay') continue;
      const g = this.g[d.id], F = this.frameFor(g);
      onDirs.add(F.key);
      if (!F.ready) continue;
      const fo = S.folders[g.dir] || {}, gw = g.new ? this.W : (fo.w || this.W), gh = g.new ? this.H : (fo.h || this.H);
      const r = g.rect || [0, 0, gw, gh], [x, y, w, h] = this.box4(r);
      Object.assign(F.wrap.style, {left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px`, zIndex: (i + 1) * 4,
        opacity: clamp(edCurve(g.opacity, S.curves, 1)(f), 0, 1)});
      F.fr.style.width = `${gw}px`; F.fr.style.height = `${gh}px`; F.fr.style.transform = `scale(${w / gw})`;
      const n = Math.max(1, fo.frames || 1), k = clamp(g.in + Math.floor((f - g.start) * (g.speed || 1) + 1e-6), 0, n - 1);
      try { F.tl.seek(k / (fo.fps || fps), false); } catch (err) { /* the graphic's own error */ }
      F.wrap.hidden = false;
    }
    for (const [k, F] of this.frames) if (!onDirs.has(k)) F.wrap.hidden = true;
    // solids (an end card's ground ...)
    for (const [d, i] of act) {
      if (d.t !== 'solid') continue;
      let el = this.solids.get(d.id);
      if (!el) { el = document.createElement('div'); el.className = 'edsolid'; this.layers.appendChild(el); this.solids.set(d.id, el); }
      const [x, y, w, h] = this.box4(d.rect), c0 = d.color == null ? [1, 1, 1] : d.color;
      const c = Array.isArray(c0) ? (c0.length >= 3 ? c0 : [c0[0] ?? 1, c0[0] ?? 1, c0[0] ?? 1]) : [+c0, +c0, +c0];
      Object.assign(el.style, {left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px`, zIndex: (i + 1) * 4,
        background: `rgb(${c.map(v => Math.round(clamp(v, 0, 1) * 255)).join(',')})`, opacity: clamp(edCurve(d.opacity, S.curves, 1)(f), 0, 1),
        mixBlendMode: d.blend === 'screen' ? 'screen' : d.blend === 'add' ? 'plus-lighter' : ''});
      el.hidden = false; onSol.add(d.id);
    }
    for (const [id, el] of this.solids) if (!onSol.has(id)) el.hidden = true;
  }
  gkey(g) { return g.dir + '\u0001' + JSON.stringify([g.values, this.capEdits[g.dir] || null, g.new]); }
  frameFor(g) {
    const fo = this.S.folders[g.dir] || {}, key = this.gkey(g);
    let F = this.frames.get(key);
    if (!F) {
      F = {wrap: document.createElement('div'), fr: document.createElement('iframe'), ready: false, tl: null, key: null};
      F.wrap.className = 'edgfx'; F.wrap.hidden = true; F.fr.title = ta('live preview'); F.fr.setAttribute('tabindex', '-1');
      F.wrap.appendChild(F.fr); this.layers.appendChild(F.wrap); this.frames.set(key, F);
    }
    if (F.key !== key) this.loadFrame(F, g, fo, key);
    return F;
  }
  async loadFrame(F, g, fo, key) {
    F.key = key; F.ready = false; F.tl = null;
    const base = '/files/' + String(g.dir).split('/').map(encodeURIComponent).join('/') + '/';
    let html = this.html.get(g.dir);
    if (!html) { try { html = await (await fetch(base + 'index.html', {cache: 'no-store'})).text(); this.html.set(g.dir, html); } catch (e) { return; } }
    if (F.key !== key) return;
    const vals = JSON.stringify(g.values || {}).replace(/</g, '\\u003c'), lgs = encodeURIComponent(logoIds(g.values).join(','));
    let doc = html.replace(/<head[^>]*>/i, m => `${m}<base href="${base}"><link rel="stylesheet" href="/fonts.css"><script src="/logos.js?b=${lgs}"><\/script><script>window.__hyperframes = {getVariables: () => (${vals})};<\/script>`);
    if (g.new) doc = doc.replace(/data-width="\d+"/, `data-width="${this.W}"`).replace(/data-height="\d+"/, `data-height="${this.H}"`);
    const ce = this.capEdits[g.dir];
    if (ce) doc = doc.replace(/(<script[^>]*captions\.js[^>]*><\/script>)/i, `$1<script>${edCapPatch(ce)}<\/script>`);
    F.fr.onload = () => {
      const w = F.fr.contentWindow;
      let n = 0;
      const ready = () => {
        if (F.key !== key) return;
        const tl = w && w.__timelines && w.__timelines.main;
        if (!tl) { if (++n < 40) setTimeout(ready, 100); return; }
        F.tl = tl; F.ready = true; this.render(this.f);
        if (w.document.fonts) w.document.fonts.ready.then(() => { if (F.key === key) this.render(this.f); });
      };
      ready();
    };
    F.fr.srcdoc = doc;
  }
  // sound effects: each one's sound (the recorded file the build will use, else the made-up one), on the timeline
  sfxUrl(q) { return q.sound ? edSoundUrl(q.sound) : `/api/editor/sound?kind=${encodeURIComponent(q.kind)}${q.dur ? `&dur=${q.dur}` : ''}`; }
  ac() { if (!this.actx) this.actx = new (window.AudioContext || window.webkitAudioContext)(); return this.actx; }
  // (destroy() closes it; nothing makes a new one after that)
  out() {                                                      // every sound effect goes through the master level
    if (!this.master) { this.master = this.ac().createGain(); this.master.gain.value = this.vol; this.master.connect(this.ac().destination); }
    return this.master;
  }
  setVolume(v) {                                               // 0..1, as the slider says it (squared: finer when quiet)
    this.vol = clamp(v, 0, 1);
    if (this.master) this.master.gain.value = this.vol;
    if (this.songEl && this.S) this.songEl.volume = this.vol * Math.min(1, Math.pow(10, ((this.S.song && this.S.song_cut) || {db: 0}).db / 20));
    this.render(this.f);
  }
  buffer(url) {
    if (this.dead) return Promise.resolve(null);
    if (!this.buf.has(url)) this.buf.set(url, fetch(url).then(r => r.ok ? r.arrayBuffer() : null).then(b => b && !this.dead && this.ac().decodeAudioData(b)).catch(() => null));
    return this.buf.get(url);
  }
  schedule(f0) {
    if (!this.S || this.S.audio_file || this.muted) return;
    const ac = this.ac(), t0 = ac.currentTime + 0.04, run = this.run = {};
    for (const q of this.S.sfx) {
      const at = (q.f - f0) / this.fps + (q.offset_s || 0);
      if (q.f < f0 - 1) continue;
      this.buffer(this.sfxUrl(q)).then(b => {
        if (!b || this.run !== run || !this.playing) return;
        const s = ac.createBufferSource(), gn = ac.createGain();
        s.buffer = b; gn.gain.value = 0.55 * Math.pow(10, (q.db || 0) / 20);
        s.connect(gn).connect(this.out());
        const when = t0 + at, now = ac.currentTime;
        if (when >= now) s.start(when); else if (now - when < b.duration) s.start(now, now - when); else return;
        this.sched.push(s);
      });
    }
  }
  unschedule() { this.run = null; this.sched.forEach(s => { try { s.stop(); } catch (e) { /* done */ } }); this.sched = []; }
  hear(url) { this.buffer(url).then(b => { if (!b || this.dead) return; const ac = this.ac(), s = ac.createBufferSource(); s.buffer = b; s.connect(this.out()); s.start(); }); }
  preroll(f) {                                                 // the next shot waits on its first frame
    const soon = f + Math.round(this.fps * 0.7);
    const nx = this.clips.find(d => d.start > f && d.start <= soon && !this.activeIds.has(d.id));
    this.preId = nx ? nx.id : null;
    if (!nx) return;
    const e = this.elFor(nx);
    if (e && !e.photo && e.at !== nx.start) { e.at = nx.start; e.v.pause(); e.v.currentTime = (edSrcAt(nx, nx.start) + 0.5) / this.fps; }
  }
  play() {
    if (this.playing || !this.S) return;
    if (this.f >= this.N - 1) this.f = 0;
    this.ac().resume().catch(() => {});
    this.playing = true; this.t0 = performance.now(); this.f0 = this.f; this.last = -1;
    this.schedule(this.f);
    if (this.songEl && !this.muted) { this.songEl.currentTime = this.f / this.fps + (this.songAt || 0); this.songEl.play().catch(() => {}); }
    const step = now => {
      if (!this.playing) return;
      const f = Math.min(this.N - 1, this.f0 + Math.floor((now - this.t0) / 1000 * this.fps));
      if (f !== this.last) { this.last = f; this.render(f); this.preroll(f); this.onFrame(f); }
      if (f >= this.N - 1) { this.pause(); return; }
      this.raf = requestAnimationFrame(step);
    };
    this.raf = requestAnimationFrame(step);
    this.onPlay(true);
  }
  pause() {
    if (!this.playing) return;
    this.playing = false; cancelAnimationFrame(this.raf); this.unschedule();
    if (this.songEl) this.songEl.pause();
    this.render(this.f, true); this.onPlay(false);
  }
  toggle() { if (this.playing) this.pause(); else this.play(); }
  seek(f) {
    f = clamp(Math.round(f), 0, Math.max(0, (this.N || 1) - 1));
    if (this.playing) { this.pause(); this.f = f; this.play(); return; }
    this.render(f, true); this.onFrame(f);
  }
  mute(on) {
    this.muted = on; if (this.songEl) this.songEl.muted = on;
    if (on) this.unschedule();
    else if (this.playing) {
      this.unschedule(); this.schedule(this.f);
      if (this.songEl) { this.songEl.currentTime = this.f / this.fps + (this.songAt || 0); this.songEl.play().catch(() => {}); }
    }
    this.render(this.f);
  }
  destroy() {
    this.pause(); this.ro.disconnect(); this.dead = true;
    for (const P of Object.values(this.pool)) for (const e of P) if (!e.photo) { e.v.removeAttribute('src'); e.v.load(); }
    if (this.songEl) { this.songEl.pause(); this.songEl.removeAttribute('src'); }
    if (this.actx) this.actx.close().catch(() => {});
  }
}
