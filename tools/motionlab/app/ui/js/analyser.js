/* MotionLab app - js/analyser.js: the Analyser page (#/analyze) and its mascots, Notes (#/note, combined notes).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ---- the Analyser's mascots (2026-10-27, the user's brief "MotionLab - Analysis Mascots" and its reference sheet):
// FLUX (Animations & Effects, a faceted blue crystal with an orbit of square nodes), SPARK (Content Creation, a golden
// origami star with a speech bubble and storyboard frames), INDEX (Notes & Knowledge, a teal orb with a lime bookmark,
// note cards on an orbit). Each = layered SVG (body, face, eyes, orbit, props apart, so each moves on its own) + CSS
// (app.css "The Analyser's mascots"): no filters (soft radial gradients instead - cheap to animate), no dependency.
// mascot(kind, {size, state, animated, cls}) -> HTML; state = idle | hover | analysing | success (data-state; a hovered
// or focused `.mhost` shows idle as hover); mascotState(el, state, ms) sets one (success / a pulse go back to idle);
// mascotsLive(root) pauses the ones off screen. Reduced motion: no continuous movement, states as static changes.
let MS_N = 0;
const MS_RM = (() => { try { return matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } })();
const MS_KINDS = {flux: 'FLUX', spark: 'SPARK', index: 'INDEX'};
// soft light: a radial gradient from a colour to nothing (the glow, the eyes' halo, the floor)
const msGlow = (id, c, a = 0.55) => `<radialGradient id="${id}"><stop offset="0" stop-color="${c}" stop-opacity="${a}"/><stop offset="1" stop-color="${c}" stop-opacity="0"/></radialGradient>`;
const msEyes = (id, x1, x2, y, rx, ry, c) => `<g class="m-eyes"><circle class="m-halo" cx="${x1}" cy="${y}" r="${ry * 1.9}" fill="url(#${id}h)"/><circle class="m-halo" cx="${x2}" cy="${y}" r="${ry * 1.9}" fill="url(#${id}h)"/>
    <g class="m-lids"><ellipse cx="${x1}" cy="${y}" rx="${rx}" ry="${ry}" fill="${c}"/><ellipse cx="${x2}" cy="${y}" rx="${rx}" ry="${ry}" fill="${c}"/></g></g>`;
// a node riding an orbit drawn as a circle squashed by `sy` (the orbit group's scale): the CSS spins carry it round,
// the reverse spins and the unsquash keep it an upright square / round dot whatever its place
const msNode = (off, inner, sy, boost = '') => `<g transform="rotate(${off})">${boost ? `<g class="${boost}">` : ''}<g transform="translate(50 0)">${boost ? `<g class="${boost} rev">` : ''}
    <g transform="rotate(${-off})"><g class="m-all rev"><g class="m-spin rev"><g transform="scale(1 ${(1 / sy).toFixed(3)})">${inner}</g></g></g></g>${boost ? '</g>' : ''}</g>${boost ? '</g>' : ''}</g>`;
function mascot(kind, {size = 112, state = 'idle', animated = true, cls = ''} = {}) {
  const id = `ms${++MS_N}`, small = size < 56;
  const wrap = svg => `<span class="masc masc-${kind}${animated && !MS_RM ? '' : ' still'}${small ? ' small' : ''}${cls ? ' ' + cls : ''}" data-state="${state}" style="--ms:${size}px" aria-hidden="true">
    <svg viewBox="0 0 120 120" width="${size}" height="${size}" focusable="false">${svg}</svg></span>`;
  if (kind === 'flux') {
    // the orbit: a circle r 50 squashed to 17 and tilted, nodes = squares; its back half behind the crystal, the front over it
    const orbit = (part, clip) => `<g transform="translate(60 58) rotate(-24) scale(1 .34)"${clip ? ` clip-path="url(#${id}f)"` : ''}>
        ${part === 'back' ? `<circle class="fx-path" r="50" fill="none" stroke="url(#${id}o)" stroke-width="1.5" vector-effect="non-scaling-stroke" opacity=".5"/>` : `<path class="fx-path" d="M50 0A50 50 0 0 1 -50 0" fill="none" stroke="url(#${id}o)" stroke-width="1.5" vector-effect="non-scaling-stroke"/>`}
        ${small ? '' : `<g class="m-spin"><g class="m-all">${[[200, 'fx-boost'], [330, ''], [75, '']].map(([o, b]) => msNode(o, `<g transform="rotate(24)"><rect class="fx-node" x="-2.8" y="-2.8" width="5.6" height="5.6" rx="1.2"/></g>`, 0.34, b)).join('')}</g></g>`}</g>`;
    return wrap(`<defs>${msGlow(id + 'g', '#4f6bff', 0.5)}${msGlow(id + 'h', '#4ff0ff', 0.7)}${msGlow(id + 'p', '#3d7bff', 0.75)}
        <linearGradient id="${id}o" x1="0" x2="1"><stop offset="0" stop-color="#38d6f5"/><stop offset="1" stop-color="#9b5cff"/></linearGradient>
        <clipPath id="${id}f" clipPathUnits="userSpaceOnUse"><rect x="-60" y="0" width="120" height="70"/></clipPath>
        <clipPath id="${id}c"><path d="M62 14L88 48L76 78L60 104L33 52L45 30Z"/></clipPath></defs>
      <ellipse class="m-floor" cx="60" cy="112" rx="30" ry="4" fill="url(#${id}p)"/>
      <circle class="m-glow" cx="60" cy="58" r="46" fill="url(#${id}g)"/>
      ${orbit('back')}
      <g class="m-float"><g class="m-tilt">
        <path d="M62 14L45 30L60 56Z" fill="#5fc8ff"/><path d="M45 30L33 52L60 56Z" fill="#3a63f2"/>
        <path d="M62 14L88 48L60 56Z" fill="#7fe0ff"/><path d="M88 48L76 78L60 56Z" fill="#5a4ff0"/>
        <path d="M76 78L60 104L60 56Z" fill="#7b3ff0"/><path d="M33 52L60 104L60 56Z" fill="#2c34c4"/>
        <path d="M62 14L88 48L76 78L60 104L33 52L45 30Z" fill="none" stroke="#a9b8ff" stroke-opacity=".35" stroke-width=".6"/>
        <path d="M62 14L60 56L33 52M60 56L88 48M60 56L60 104" fill="none" stroke="#c4d6ff" stroke-opacity=".28" stroke-width=".5"/>
        <g clip-path="url(#${id}c)"><path class="fx-sweep" d="M14 0h12L4 120h-12Z" fill="#e8f6ff" opacity="0"/>
          <rect class="m-flash" x="0" y="0" width="120" height="120" fill="#fff" opacity="0"/></g>
        <path d="M44.5 51.5Q59 42 74 51.5Q76 64 59 70.5Q42 64 44.5 51.5Z" fill="#060919" stroke="#1d2c74" stroke-width=".7"/>
        ${msEyes(id, 53, 65, 57, 3.1, 5.6, '#7ff4ff')}</g></g>
      ${orbit('front', true)}`);
  }
  if (kind === 'spark') {
    return wrap(`<defs>${msGlow(id + 'g', '#ffa31a', 0.42)}${msGlow(id + 'h', '#ffd84a', 0.75)}${msGlow(id + 'p', '#ff9a1a', 0.7)}
        <linearGradient id="${id}b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffc35a"/><stop offset="1" stop-color="#ff8a3d"/></linearGradient></defs>
      <ellipse class="m-floor" cx="58" cy="112" rx="28" ry="4" fill="url(#${id}p)"/>
      <circle class="m-glow" cx="58" cy="56" r="46" fill="url(#${id}g)"/>
      <circle class="sp-burst" cx="58" cy="56" r="30" fill="none" stroke="#ffd36a" stroke-width="2" opacity="0"/>
      ${small ? '' : `<g class="sp-rays" stroke="#ffc83a" stroke-width="2.6" stroke-linecap="round"><path d="M22 26L28 33"/><path d="M14 44L22 46"/><path d="M96 74L104 70"/></g>`}
      <g class="m-float"><g class="m-tilt">
        <path d="M60 58L55.1 11.3L47.5 43.7Z" fill="#ffe27a"/><path d="M60 58L55.1 11.3L70.1 41.9Z" fill="#ffcf45"/>
        <path d="M60 58L101.3 43L70.1 41.9Z" fill="#ffa232"/><path d="M60 58L101.3 43L78.4 62.9Z" fill="#ff7c2c"/>
        <path d="M60 58L85.7 88.6L78.4 62.9Z" fill="#f2563f"/><path d="M60 58L85.7 88.6L60.7 77Z" fill="#e3434a"/>
        <path d="M60 58L35.3 92L60.7 77Z" fill="#ff6c36"/><path d="M60 58L35.3 92L42.1 64.5Z" fill="#ff922a"/>
        <path d="M60 58L13.4 46.4L42.1 64.5Z" fill="#ffbf3c"/><path d="M60 58L13.4 46.4L47.5 43.7Z" fill="#ffd95a"/>
        <path d="M55.1 11.3L70.1 41.9L101.3 43L78.4 62.9L85.7 88.6L60.7 77L35.3 92L42.1 64.5L13.4 46.4L47.5 43.7Z" fill="none" stroke="#fff0b8" stroke-opacity=".35" stroke-width=".6"/>
        <path class="m-flash" d="M55.1 11.3L70.1 41.9L101.3 43L78.4 62.9L85.7 88.6L60.7 77L35.3 92L42.1 64.5L13.4 46.4L47.5 43.7Z" fill="#fff6d0" opacity="0"/>
        <ellipse cx="60" cy="59" rx="15" ry="11.5" fill="#1a0d06" stroke="#5a2a10" stroke-width=".7"/>
        ${msEyes(id, 54.6, 65.4, 58.6, 2.9, 5.1, '#ffe38a')}
        <path class="sp-glint" d="M55 4l1.4 4.4l4.4 1.4l-4.4 1.4L55 15.6l-1.4-4.4l-4.4-1.4l4.4-1.4Z" fill="#fff4c2"/></g></g>
      ${small ? '' : `<g class="sp-bub"><g class="sp-bubin"><path d="M84 12h26a4 4 0 0 1 4 4v12a4 4 0 0 1-4 4H95l-6 6v-6h-5a4 4 0 0 1-4-4V16a4 4 0 0 1 4-4Z" fill="url(#${id}b)"/>
          <rect x="86" y="18" width="20" height="2.6" rx="1.3" fill="#fff" opacity=".85"/><rect x="86" y="24" width="13" height="2.6" rx="1.3" fill="#ff5a3a" opacity=".8"/></g></g>
        <g class="sp-frames">${[0, 1, 2].map(i => `<g class="sp-fr f${i}"><rect x="${80 + i * 12.5}" y="88" width="11" height="13" rx="1.6" fill="#2a2140" stroke="#a27bff" stroke-width="1"/>
          ${i === 1 ? `<path d="M96.4 91.5l4.5 3l-4.5 3Z" fill="#c7b2ff"/>` : `<path d="M${81.8 + i * 12.5} 99l3-3.6l2.2 2.2l1.6-1.6l2.4 3Z" fill="#8a6fd1"/>`}</g>`).join('')}
          <rect class="sp-link" x="80" y="94" width="36" height="1.2" rx=".6" fill="#ffe08a" opacity="0"/></g>`}`);
  }
  // INDEX: an orbit r 52 x 46 (round enough to turn whole), its dots, three note cards placed by CSS (app.css: --x --y --r)
  return wrap(`<defs>${msGlow(id + 'g', '#2fe0b4', 0.42)}${msGlow(id + 'h', '#8dffe6', 0.75)}${msGlow(id + 'p', '#2fd6b8', 0.7)}
      <radialGradient id="${id}b" cx=".36" cy=".3" r=".75"><stop offset="0" stop-color="#c8ffef"/><stop offset=".38" stop-color="#58e6c4"/><stop offset=".75" stop-color="#1fae9f"/><stop offset="1" stop-color="#0e6670"/></radialGradient>
      <linearGradient id="${id}k" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#d9f99d"/><stop offset="1" stop-color="#84cc16"/></linearGradient></defs>
    <ellipse class="m-floor" cx="60" cy="112" rx="28" ry="4" fill="url(#${id}p)"/>
    <circle class="m-glow" cx="60" cy="60" r="48" fill="url(#${id}g)"/>
    <g class="ix-orbit"><ellipse cx="60" cy="60" rx="53" ry="45" fill="none" stroke="#2fd6b8" stroke-opacity=".55" stroke-width=".9"/>
      ${small ? '' : [[113, 60], [60, 15], [7, 60], [86, 99]].map(([x, y]) => `<circle class="ix-dot" cx="${x}" cy="${y}" r="2.3" fill="#6ff5d6"/>`).join('')}</g>
    <g class="m-float"><g class="m-tilt"><g class="ix-orb">
      <path d="M33 61C23 64 20 75 25 83C30 76 34 70 38 66Z" fill="#2fcf8f"/>
      <circle cx="60" cy="60" r="31" fill="url(#${id}b)"/>
      <circle cx="67" cy="67" r="25" fill="#2fd6b8" opacity=".22"/>
      <ellipse cx="50" cy="40" rx="12" ry="6" fill="#eafff8" opacity=".35" transform="rotate(-24 50 40)"/>
      <path class="m-flash" d="M60 29a31 31 0 1 1 0 62a31 31 0 1 1 0-62Z" fill="#e6fff8" opacity="0"/>
      <ellipse cx="60" cy="59" rx="17.5" ry="13.5" fill="#03201e" stroke="#0d4d48" stroke-width=".7"/>
      ${msEyes(id, 54, 66, 58.5, 3.2, 5.6, '#8dffe6')}
      <g class="ix-mark"><path d="M54.8 86h10.4v19l-5.2-4.4l-5.2 4.4Z" fill="url(#${id}k)"/><path class="ix-markhi" d="M54.8 86h10.4v19l-5.2-4.4l-5.2 4.4Z" fill="#f7ffd6" opacity="0"/></g></g></g></g>
    ${small ? '' : `<g class="ix-cards">${[['c1', '#c7f8ec'], ['c2', '#d4f7b5'], ['c3', '#a7efe1']].map(([c, f]) => `<g class="ix-card ${c}"><g class="ix-drift">
        <rect x="-11" y="-8.5" width="22" height="17" rx="3.2" fill="${f}" opacity=".9"/>
        ${[0, 1, 2].map(i => `<rect class="ix-ln l${i}" x="-7" y="${-4.3 + i * 4.2}" width="${[14, 11, 13][i]}" height="1.9" rx=".95" fill="#1f8f84" opacity=".75"/>`).join('')}</g></g>`).join('')}</g>`}`);
}
function mascotState(el, state, ms) {
  if (!el) return;
  clearTimeout(el._mst);
  el.dataset.state = state;
  if (state === 'success' || ms) el._mst = setTimeout(() => { el.dataset.state = 'idle'; }, ms || 900);
}
function mascotsLive(root) {                 // the ones off screen stop moving (IntersectionObserver), back when seen
  if (MS_RM || !('IntersectionObserver' in window)) return () => {};
  const io = new IntersectionObserver(es => es.forEach(e => e.target.classList.toggle('paused', !e.isIntersecting)));
  $$('.masc:not(.still)', root).forEach(m => io.observe(m));
  return () => io.disconnect();
}
// the Analyser's ways and their pages (2026-10-27, the user: "the corresponding videos analyzed from a specific topic
// (flux, spark, or index) they each have their own section? kinda like when i click on a video i had notes with index
// and the character appears in a new page?"; then "dont remove the existing tabs of stuff, cuz people would not know
// where to look for"): #/analyze = the three mascot ways, the smaller row, what runs and waits, and the tabs with their
// lists as before; a way (its card, its title, its count) opens its own page (#/analyze/videos = FLUX, /spark,
// /notes = INDEX, /thumbs, /texts) with the mascot in its header, its jobs and the same list. Thumbnails and Scripts & prompts stay apart, without a mascot (the user: "for now lets just keep
// thumbnails and scripts & prompts separate"), their buttons *Analyze thumbnails* / *Analyze scripts & prompts*.
const AN_MODES = {
  videos: {kind: 'flux', title: t('Animations & Effects'), text: t('Breaks down motion, timing, transitions and visual effects.')},
  spark: {kind: 'spark', title: t('Content Creation'), text: t("Why a video worked: its hook, its story and its numbers against the creator's usual.")},
  notes: {kind: 'index', title: t('Notes & Knowledge'), text: t('Creates useful summaries, informative notes and reusable Markdown context.')}};
const AN_EXTRA = {
  thumbs: {icon: 'thumb', title: t('Thumbnails'), text: t('A channel, some videos or your pictures: what they have in common.')},
  texts: {icon: 'texts', title: t('Scripts & prompts'), text: t('Up to {n} prompts, scripts or hooks, each checked part by part.', {n: TX_MAX})}};
const anHref = k => '#/analyze/' + k;
const anIsFx = j => j.kind === 'analyze' || (j.kind === 'download' && !['notes', 'spark'].includes(j.then_kind));     // FLUX's page: its downloads too
const anFxWork = j => j.kind === 'analyze' || (j.kind === 'download' && j.then && !['notes', 'spark'].includes(j.then_kind));   // FLUX at work
const anIsNt = j => j.kind === 'notes' || (j.kind === 'download' && j.then_kind === 'notes');
const anIsSp = j => j.kind === 'spark' || j.kind === 'spark_numbers' || (j.kind === 'download' && j.then_kind === 'spark');
const AN_SEEN = new Set();                    // the jobs whose success a mascot already showed
// a mascot's state from the jobs: one of its kind running = analysing, one that just ended well (shown once) = success
function anState(JOBS, f) {
  if (JOBS.some(j => f(j) && ['running', 'queued', 'cancelling'].includes(j.status))) return 'analysing';
  const done = JOBS.filter(j => f(j) && j.kind !== 'download' && j.status === 'done' && j.ended_ago_s != null && j.ended_ago_s < 10 && !AN_SEEN.has(jobKey(j)));
  done.forEach(j => AN_SEEN.add(jobKey(j)));
  return done.length ? 'success' : 'idle';
}
const anBtn = {
  videos: () => `<button class="btn pri" id="an" title="${ta('Links or video files, up to {n} at a time', {n: AV_MAX})}"><svg class="i"><use href="#i-analyze"/></svg>${t('Add videos')}</button><button class="btn ghost" id="dl" title="${ta('Download a video or a song (MP3) from a link without analysing it - e.g. music for an edit')}"><svg class="i"><use href="#i-download"/></svg>${t('Download from link')}</button>`,
  spark: () => `<button class="btn pri" id="spadd" title="${ta("Links or video files: why each one worked, against its creator's usual")}"><svg class="i"><use href="#i-sparkle"/></svg>${t('Analyze with SPARK')}</button>`,
  notes: () => `<button class="btn pri" id="ntadd"><svg class="i"><use href="#i-pen"/></svg>${t('Take notes')}</button>`,
  thumbs: () => `<button class="btn" id="tadd"><svg class="i"><use href="#i-thumb"/></svg>${t('Analyze thumbnails')}</button><button class="btn ghost" id="ttest" title="${ta('See your thumbnail on a YouTube-like home page, next to the newest videos of big creators - does it pop?')}"><svg class="i"><use href="#i-play"/></svg>${t('Preview your thumbnail')}</button>`,
  texts: () => `<button class="btn" id="txadd"><svg class="i"><use href="#i-texts"/></svg>${t('Analyze scripts & prompts')}</button>`};
function anWire(main, draw) {                  // the buttons any Analyser page may have
  const on = (id, fn) => { const b = $(id, main); if (b) b.onclick = fn; };
  on('#an', () => addVideosModal()); on('#dl', downloadModal); on('#ntadd', () => addNotesModal()); on('#spadd', () => addSparkModal());
  on('#tadd', () => addThumbsModal()); on('#ttest', () => thumbTest()); on('#txadd', () => addTextsModal());
  wireGo(main);
  if (draw) wireBatchRows(main, draw);
}
function wireGo(root) {                         // a card / way opens its page (not when its own button is clicked)
  $$('[data-go]', root).forEach(c => c.onclick = e => { if (!e.target.closest('button, a, select, input, label')) location.hash = c.dataset.go; });
}
async function pageRefs(main, tab) {
  return tab ? anSection(main, tab) : anOverview(main);
}
// the lists, the same on the overview's tabs and on a way's own page: D = what the page fetched, F = its filters
const AN_TABS = [['videos', t('Effects'), 'film'], ['spark', t('Why it worked'), 'sparkle'], ['notes', t('Notes'), 'pen'], ['thumbs', t('Thumbnails'), 'thumb'], ['texts', t('Scripts & prompts'), 'texts']];
// Search and filters on the three ways' lists (2026-11-10, the user: "for the videos already analyzed (either from
// index, spark or flux) add some filters so i can roam around them notes, and maybe a search bar"): one row - the
// search (every word must be found: the names, the channel, the tags, and what Claude wrote - a note's TL;DR,
// takeaways and sections, a SPARK's verdict and take-aways: the server's `find`), Claude's state, the platform, the
// tags, each way's own (FLUX focus / category, Notes their kind, SPARK the result) and the order. Typing or picking
// redraws the cards only (`anCards`): nothing is fetched again, the search box keeps the focus. The order is kept on
// this PC (ml.anSort.<way>); the rest lasts while MotionLab is open (`AN_F`).
const AN_SORT = {new: t('Newest first'), old: t('Oldest first'), az: t('A to Z'), long: t('Longest first'), short: t('Shortest first')};
const AN_CARD = {videos: r => refCard(r), notes: n => noteCard(n), spark: s => sparkCard(s)};
let AN_LAST = {k: '', items: []};                // the list on the page: the cards are drawn again from it
const anItems = (k, D) => k === 'videos' ? D.all : k === 'notes' ? D.NOTES : D.SPARK;
const anReady = (k, x) => k === 'videos' ? (x.flow || {}).next !== 'claude' : x.status === 'ready';
const anName = (k, x) => (k === 'videos' ? x.label || x.title : k === 'notes' ? (x.notes && x.notes.title) || x.label : (x.spark && x.spark.title) || x.label) || '';
const anFind = (k, x) => k === 'videos' ? [x.label, x.title, x.name, t(x.category_label || ''), (x.tags || []).join(' '), x.platform, ...Object.values(x.lines || {})].join(' ').toLowerCase()
  : (x.find || [x.label, x.title, x.uploader, (x.tags || []).join(' ')].join(' ').toLowerCase());
const anWhenOf = (k, x) => strTime(k === 'videos' ? x.generated : x.created);
const anFiltered = F => !!((F.q || '').trim() || F.st || F.plat || F.tag || F.cat || F.foc || F.nk || F.res);
function anFilter(k, items, F) {
  const words = (F.q || '').toLowerCase().split(/\s+/).filter(Boolean);
  const rows = items.filter(x => (!words.length || words.every(w => anFind(k, x).includes(w)))
    && (!F.st || (F.st === 'ready') === anReady(k, x)) && (!F.plat || (x.platform || '') === F.plat)
    && (!F.tag || (x.tags || []).includes(F.tag)) && (!F.cat || x.category === F.cat) && (!F.foc || x.focus === F.foc)
    && (!F.nk || (x.notes || {}).kind === F.nk) && (!F.res || (x.result || 'unknown') === F.res));
  const by = F.sort || 'new', dur = x => x.duration_s || 0;
  return rows.sort((a, b) => by === 'old' ? anWhenOf(k, a) - anWhenOf(k, b) : by === 'az' ? anName(k, a).localeCompare(anName(k, b), LANG)
    : by === 'long' ? dur(b) - dur(a) : by === 'short' ? dur(a) - dur(b) : anWhenOf(k, b) - anWhenOf(k, a));
}
function anCards(k, F) {
  const rows = anFilter(k, AN_LAST.items, F);
  return {n: rows.length, html: rows.length ? `<div class="cards pcards">${rows.map(AN_CARD[k]).join('')}</div>`
    : `<div class="empty">${t('Nothing matches.')} <a href="#" data-fclear>${t('Clear the search and filters')}</a></div>`};
}
function anFilterRow(k, items, F, tail = '') {
  const sel = (id, all, opts, v) => `<select id="${id}" class="ffil">${`<option value="">${all}</option>`}${opts.map(([o, l, n]) => `<option value="${esc(o)}" ${o === v ? 'selected' : ''}>${esc(l)}${n != null ? ` (${n})` : ''}</option>`).join('')}</select>`;
  const count = (f, v) => items.filter(x => f(x) === v).length;
  const plats = [...new Set(items.map(x => x.platform).filter(Boolean))].sort(), tags = [...new Set(items.flatMap(x => x.tags || []))].sort();
  const waitWord = k === 'videos' ? t('Not checked by Claude yet') : t('Waiting for Claude');
  const own = k === 'videos'
    ? sel('ffoc', t('Every focus'), Object.entries(FOCUS_SHORT).map(([f, l]) => [f, l, count(x => x.focus, f)]).filter(o => o[2]), F.foc)
      + sel('fcat', t('All categories ({n})', {n: items.length}), [...new Map(items.filter(r => r.category).map(r => [r.category, r.category_label])).entries()].map(([c, l]) => [c, t(l || ''), count(x => x.category, c)]), F.cat)
    : k === 'notes' ? (() => { const kinds = [...new Set(items.map(x => (x.notes || {}).kind).filter(Boolean))];
        return kinds.length > 1 ? sel('fnk', t('Every kind'), kinds.map(c => [c, NKIND[c] || c, count(x => (x.notes || {}).kind, c)]), F.nk) : ''; })()
    : (() => { const res = Object.keys(SP_RESULT).filter(r => items.some(x => (x.result || 'unknown') === r));
        return res.length > 1 ? sel('fres', t('Every result'), res.map(r => [r, SP_RESULT[r], count(x => x.result || 'unknown', r)]), F.res) : ''; })();
  return `<div class="row frow anfil">
      <label class="ansearch"><svg class="i"><use href="#i-search"/></svg><input type="search" id="fq" value="${esc(F.q || '')}" placeholder="${ta(k === 'videos' ? 'Search names, categories, tags…' : 'Search names, channels, tags and what Claude wrote…')}" autocomplete="off"></label>
      ${sel('fst', t('Any state'), [['ready', k === 'videos' ? t('Checked by Claude') : t('Ready')], ['claude', waitWord]], F.st)}
      ${plats.length > 1 ? sel('fplat', t('Every platform'), plats.map(p => [p, p, count(x => x.platform, p)]), F.plat) : ''}
      ${tags.length ? sel('ftag', t('All tags'), tags.map(g => [g, g]), F.tag) : ''}${own}
      ${sel('fsort', AN_SORT.new, Object.entries(AN_SORT).slice(1), F.sort === 'new' ? '' : F.sort)}
      <span class="grow"></span><span class="small dim" id="fcount"></span>${tail}</div>`;
}
function anList(k, D, F) {
  if (k === 'videos' || k === 'notes' || k === 'spark') {
    const items = anItems(k, D) || [];
    AN_LAST = {k, items};
    if (F.sort === undefined) F.sort = anPref('anSort.' + k) || 'new';
    const tail = k === 'videos' ? `<label class="chk small dim"><input type="checkbox" id="tests" ${F.tests ? 'checked' : ''}> ${t('show the test videos')}</label>`
      : k === 'notes' && items.filter(n => n.status === 'ready').length >= 2 ? `<button class="btn" id="ncombine" title="${ta('Several videos on one topic: one Markdown file with all their notes, or one question to Claude across them')}"><svg class="i"><use href="#i-copy"/></svg>${t('Combine notes…')}</button>` : '';
    if (!items.length) return (tail ? `<div class="row frow"><span class="grow"></span>${tail}</div>` : '') + `<div class="pcempty">${{videos: t('The videos you analyse land here - <i>Add videos</i> above.'),
      notes: t('The notes you take land here - <i>Take notes</i> above: a link or a video file.'),
      spark: t('Why your references worked lands here - <i>Analyze with SPARK</i> above: a link or a video file.')}[k]}</div>`;
    return `${anFilterRow(k, items, F, tail)}${k === 'notes' ? '<div id="ncomb"></div>' : ''}<div id="ancards">${anCards(k, F).html}</div>`;
  }
  if (k === 'thumbs') {
    return D.SETS.length ? `<div class="cards pcards">${D.SETS.map(setCard).join('')}</div>`
      : `<div class="pcempty">${t('Thumbnail sets land here - <i>Analyze thumbnails</i> above: a channel, some videos or your pictures.')}</div>`;
  }
  return D.TXS.length ? `<div class="cards pcards">${D.TXS.map(textSetCard).join('')}</div>`
    : `<div class="pcempty">${t('Your sets of scripts and prompts land here - <i>Analyze scripts & prompts</i> above.')}</div>`;
}
function anListWire(main, F, draw, wait) {      // the filters and bars a list may have
  const on = (id, ev, fn) => { const x = $(id, main); if (x) x[ev] = fn; };
  on('#wbar', 'onclick', () => waitingModal(wait));
  on('#tests', 'onchange', e => { F.tests = e.target.checked; draw(); });
  const k = AN_LAST.k, box = $('#ancards', main);
  if (box) {                                    // the search and filters: the cards drawn again, nothing fetched
    const cards = () => { const C = anCards(k, F); box.innerHTML = C.html; wireGo(box);
      $('#fcount', main).textContent = anFiltered(F) ? t('{n} of {total}', {n: C.n, total: AN_LAST.items.length}) : '';
      $$('[data-fclear]', box).forEach(a => a.onclick = e => { e.preventDefault(); Object.assign(F, {q: '', st: '', plat: '', tag: '', cat: '', foc: '', nk: '', res: ''});
        $$('.anfil select', main).forEach(s => { if (s.id !== 'fsort') s.value = ''; }); $('#fq', main).value = ''; cards(); }); };
    const pick = {fst: 'st', fplat: 'plat', ftag: 'tag', ffoc: 'foc', fcat: 'cat', fnk: 'nk', fres: 'res'};
    Object.entries(pick).forEach(([id, key]) => on('#' + id, 'onchange', e => { F[key] = e.target.value; cards(); }));
    on('#fsort', 'onchange', e => { F.sort = e.target.value || 'new'; anPref('anSort.' + k, F.sort); cards(); });
    on('#fq', 'oninput', e => { F.q = e.target.value; cards(); });
    on('#fq', 'onfocus', () => { F.focusQ = true; });           // a redraw (a job ended, the live page) keeps typing there
    on('#fq', 'onblur', () => { F.focusQ = false; });
    on('#fq', 'onkeydown', e => { if (e.key === 'Escape' && e.target.value) { e.stopPropagation(); e.target.value = ''; F.q = ''; cards(); } });
    cards();
    if (F.focusQ) { const q = $('#fq', main); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
  }
  on('#ncombine', 'onclick', () => combineModal());
  const nc = $('#ncomb', main);
  if (nc) api('/api/notes-combined').then(L => { nc.innerHTML = L.length ? `<div class="ncombl"><span class="small muted">${t('Across videos')}</span>${L.map(c => `<a class="ncombc" href="#/notes-combined/${encodeURIComponent(c.id)}">
      <svg class="i"><use href="#i-claude"/></svg><span class="grow">${esc(c.answer ? c.answer.title : c.q)}</span><span class="small dim">${tn((c.names || []).length, '{n} video', '{n} videos')} · ${c.answer ? t('answered') : t('waiting for Claude')}</span></a>`).join('')}</div>` : ''; }).catch(() => {});
}
const anWaitBar = wait => { const wv = wait.filter(w => !w.photo && !w.audio).length;
  return wait.length ? `<button class="wbar" id="wbar"><svg class="i"><use href="#i-download"/></svg><span class="grow">${wv ? tn(wv, '<b>{n} downloaded video</b> waits to be analysed', '<b>{n} downloaded videos</b> wait to be analysed') : tn(wait.length, '<b>{n} download</b> not analysed', '<b>{n} downloads</b> not analysed')}</span><span class="wgo">${t('Show them →')}</span></button>` : ''; };
const anPref = (k, v) => { try { if (v === undefined) return localStorage.getItem('ml.' + k); localStorage.setItem('ml.' + k, v); } catch (e) { /* storage blocked */ } return null; };
// the overview: the ways, then - as before (the user: "dont remove the existing tabs of stuff, cuz people would not
// know where to look for") - what runs / is left / waits and one tab per kind with its list (the tab shown is
// remembered, ml.anTab; the addresses #/analyze/<kind> are the ways' own pages)
// a list's search and filters while MotionLab is open: a live redraw (route(true)) or coming back keeps them
const AN_F = {};
const anF = key => AN_F[key] || (AN_F[key] = {tests: false, cat: '', tag: '', foc: ''});
async function anOverview(main) {
  let stop = null, tab = AN_TABS.some(x => x[0] === anPref('anTab')) ? anPref('anTab') : 'videos';
  const F = anF('overview');
  onCleanup(() => stop && stop());
  const draw = async () => {
    const [all, wait, BAT, SETS, TXS, NOTES, JOBS, SPARK] = await Promise.all([api('/api/references' + (F.tests ? '?tests=1' : '')), api('/api/waiting').catch(() => []),
      api('/api/batches?kind=review').catch(() => []), api('/api/thumbs').catch(() => []), api('/api/texts').catch(() => []),
      api('/api/notes').catch(() => []), api('/api/jobs').catch(() => []), api('/api/spark').catch(() => [])]);
    const MST = {videos: anState(JOBS, anFxWork), notes: anState(JOBS, anIsNt), spark: anState(JOBS, anIsSp)};
    // each way's foot: what is there, what is left for Claude, what waits - only when its kind has something
    const vLeft = all.filter(r => (r.flow || {}).next === 'claude').length, sLeft = SETS.filter(s => !s.has_style).length;
    const nThumbs = SETS.reduce((a, s) => a + (s.count || 0), 0), nTexts = TXS.reduce((a, s) => a + (s.count || 0), 0);
    const tLeft = TXS.reduce((a, s) => a + Math.max(0, (s.count || 0) - (s.checked || 0)), 0);
    const nLeft = NOTES.filter(n => n.status === 'claude').length, spLeft = SPARK.filter(n => n.status === 'claude').length;
    const none = !all.length && !wait.length && !SETS.length && !TXS.length && !NOTES.length && !SPARK.length;
    const feet = {videos: all.length ? tn(all.length, '{n} video analysed', '{n} videos analysed') + (vLeft ? ' · ' + t('{n} not checked by Claude yet', {n: vLeft}) : '') : '',
      notes: NOTES.length ? tn(NOTES.length, '{n} video with notes', '{n} videos with notes') + (nLeft ? ' · ' + t('{n} waiting for Claude', {n: nLeft}) : '') : '',
      spark: [SPARK.length > spLeft ? tn(SPARK.length - spLeft, '{n} video explained', '{n} videos explained') : '', spLeft ? t('{n} waiting for Claude', {n: spLeft}) : ''].filter(Boolean).join(' · '),
      thumbs: SETS.length ? `${plural(SETS.length, 'set')} · ${plural(nThumbs, 'thumbnail')}${sLeft ? ' · ' + t('{n} without patterns yet', {n: sLeft}) : ''}` : '',
      texts: TXS.length ? `${plural(TXS.length, 'set')} · ${tn(nTexts, '{n} script & prompts', '{n} scripts & prompts')}${tLeft ? ' · ' + t('{n} not checked yet', {n: tLeft}) : ''}` : ''};
    const counts = {videos: all.length, spark: SPARK.length, notes: NOTES.length, thumbs: SETS.length, texts: TXS.length};
    const anyFoot = feet.videos || feet.notes || feet.spark;
    const way = k => { const M = AN_MODES[k];
      return `<div class="gway anway mhost w-${k}${M.soon ? ' soon' : ''}" data-go="${anHref(k)}">
        ${M.soon ? `<span class="soonchip">${t('Coming soon')}</span>` : ''}${mascot(M.kind, {size: 116, state: MST[k]})}
        <div class="mname">${MS_KINDS[M.kind]}</div><h2><a href="${anHref(k)}">${M.title}</a></h2>
        <p>${M.text}</p><div class="row">${anBtn[k]()}</div>${feet[k] ? `<a class="gway-foot" href="${anHref(k)}">${feet[k]} →</a>`
          : anyFoot ? '<span class="gway-foot blank" aria-hidden="true">&nbsp;</span>' : ''}</div>`; };      // keeps the buttons in line
    const mini = k => { const M = AN_EXTRA[k];
      return `<div class="gway gmw" data-go="${anHref(k)}"><svg class="ic"><use href="#i-${M.icon}"/></svg>
        <div class="grow gmt"><h2><a href="${anHref(k)}">${M.title}</a></h2><p>${M.text}</p>${feet[k] ? `<a class="gway-foot" href="${anHref(k)}">${feet[k]} →</a>` : ''}</div><div class="row">${anBtn[k]()}</div></div>`; };
    main.innerHTML = `<div class="head"><div><h1>${t('Analyser')}</h1><div class="sub">${t('Three ways to learn from a video - its effects, why it works, what it teaches - plus thumbnails, scripts and prompts. Measured by MotionLab, explained by Claude, remembered for your own videos.')}</div></div></div>
      <div class="gways g3 anways">${way('videos')}${way('spark')}${way('notes')}</div>
      <div class="gways g2 gmini">${mini('thumbs')}${mini('texts')}</div>
      <div id="avprog"></div><div id="anfail"></div>${batchRows(BAT)}${anWaitBar(wait)}
      ${none ? `<div class="row frow"><span class="grow"></span><label class="chk small dim"><input type="checkbox" id="tests" ${F.tests ? 'checked' : ''}> ${t('show the test videos')}</label></div>`
        : `<div class="tabs antabs">${AN_TABS.map(([k, l, ic]) => `<a href="${anHref(k)}" data-antab="${k}" class="${tab === k ? 'on' : ''}"><svg class="i"><use href="#i-${ic}"/></svg>${l} <span class="dim">${counts[k]}</span></a>`).join('')}</div>
          <div id="antab">${anList(tab, {all, NOTES, SETS, TXS, SPARK}, F)}</div>`}`;
    anWire(main, draw);
    anListWire(main, F, draw, wait);
    failedBar($('#anfail', main), '', draw);
    $$('[data-antab]', main).forEach(a => a.onclick = e => { e.preventDefault(); tab = a.dataset.antab; anPref('anTab', tab);
      Object.assign(F, {q: '', st: '', plat: '', tag: '', cat: '', foc: '', nk: '', res: '', sort: undefined, focusQ: false}); draw(); });   // each tab its own filters
    if (stop) stop();
    const live = mascotsLive(main), prog = progressPanel($('#avprog', main), () => draw(), ['download', 'analyze', 'notes', 'spark', 'spark_numbers', ...THUMBS_JOBS]);
    stop = () => { prog(); live(); };
    $$('.masc[data-state=success]', main).forEach(m => mascotState(m, 'success'));       // then back to idle
  };
  await draw();
}
// one way's page: FLUX / SPARK / INDEX open with their mascot (it greets you, works while its jobs run, lights up when
// one ends well); Thumbnails and Scripts & prompts with the page head every sub page has
async function anSection(main, k) {
  const M = AN_MODES[k], X = AN_EXTRA[k];
  const F = anF(k);
  let first = true, stop = null;
  onCleanup(() => stop && stop());
  const head = state => M ? `<div class="anhead mhost w-${k}">${mascot(M.kind, {size: 92, state})}
      <div class="grow"><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> /</div><div class="mname">${MS_KINDS[M.kind]}</div>
        <h1>${M.title}</h1><div class="sub">${M.text}</div></div>
      <div class="row">${anBtn[k]()}</div></div>`
    : `<div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> /</div><h1>${X.title}</h1><div class="sub">${X.text}</div></div>
      <div class="row">${anBtn[k]()}</div></div>`;
  const draw = async () => {
    let body = '', JOBS = [], kinds = [], match = () => true, wait = [], state = 'idle';
    if (k === 'videos') {
      let all, BAT;
      [all, wait, BAT, JOBS] = await Promise.all([api('/api/references' + (F.tests ? '?tests=1' : '')), api('/api/waiting').catch(() => []),
        api('/api/batches?kind=review').catch(() => []), api('/api/jobs').catch(() => [])]);
      kinds = ['download', 'analyze']; match = anIsFx; state = anState(JOBS, anFxWork);
      body = `${batchRows(BAT)}${anWaitBar(wait)}${anList('videos', {all}, F)}`;
    } else if (k === 'notes') {
      let NOTES;
      [NOTES, JOBS] = await Promise.all([api('/api/notes').catch(() => []), api('/api/jobs').catch(() => [])]);
      kinds = ['download', 'notes']; match = anIsNt; state = anState(JOBS, anIsNt);
      body = anList('notes', {NOTES}, F);
    } else if (k === 'spark') {
      let SPARK;
      [SPARK, JOBS] = await Promise.all([api('/api/spark').catch(() => []), api('/api/jobs').catch(() => [])]);
      kinds = ['download', 'spark', 'spark_numbers']; match = anIsSp; state = anState(JOBS, anIsSp);
      body = anList('spark', {SPARK}, F);
    } else if (k === 'thumbs') {
      kinds = THUMBS_JOBS;
      body = anList('thumbs', {SETS: await api('/api/thumbs').catch(() => [])}, F);
    } else {
      body = anList('texts', {TXS: await api('/api/texts').catch(() => [])}, F);
    }
    main.innerHTML = `${head(state)}<div id="avprog"></div><div id="anfail"></div>${body}`;
    anWire(main, draw);
    anListWire(main, F, draw, wait);
    if (M) failedBar($('#anfail', main), k, draw);              // what did not work, kept to try again later
    if (stop) stop();
    const live = mascotsLive(main), prog = PIPE[k] ? pipePanel($('#avprog', main), () => draw(), match, k)     // FLUX, SPARK, INDEX: progress bars
      : kinds.length ? progressPanel($('#avprog', main), () => draw(), kinds, match) : () => {};
    stop = () => { prog(); live(); };
    const m = $('.anhead .masc', main);
    if (m && m.dataset.state === 'success') mascotState(m, 'success');
    else if (m && first && m.dataset.state === 'idle') mascotState(m, 'hover', 700);     // it greets you once
    first = false;
  };
  await draw();
}

// ---- Notes (the Analyser's third way, 2026-10-27; the design: docs\plans.md 0.6.5 *Notes - the research*, the user:
// "simple and effective", "like a professional, not crowded", "video at 720p with option to delete the video afterwards
// but keep the notes", no test-yourself questions). analysis\notes\<name>\ - motionlab\notes.py; Claude = /take-notes
const nTime = (f, fps, quote = '', rep = false) => f == null ? '' : `<a href="#" class="ntime" data-f="${f}"${quote ? ` title="${esc('“' + quote + '”')}"` : ''}>f${f} (${tc(f, fps)})</a>${rep ? `<span class="nrep" title="${ta("YouTube's Most replayed: viewers watch this part again")}">${t('most replayed')}</span>` : ''}`;
// a section's colour (the notes page, 2026-10-29): its block, its piece of the map, the takeaways and steps said in it
const NCOL = ['#38d6f5', '#b8f03c', '#a78bfa', '#ffb547', '#ff7aa8', '#3ecf8e', '#4fb3ff', '#ff8a5c'];
const NKIND = {tutorial: t('Tutorial'), lecture: t('Lecture / explainer'), interview: t('Interview / podcast'), list: t('List'),
  opinion: t('Opinion / news'), story: t('Story'), other: t('Other|kind')};
// Ask Claude's questions and answers (2026-10-29, the user: "a posibility to run a prompt fo that video notes (imagine i
// wanted to expand on some topic)"): what the video says (quoted, each point plays its moment) apart from what Claude
// adds from its own knowledge. One video's (src = {fps}) or across several (src = {names: {name: {fps, title, i}}})
function diveHtml(a, i, cmd, src) {
  const A = a.answer, many = !!src.names;
  const chip = p => { if (!many) return nTime(p.at, src.fps, p.quote || '', p.replayed);
    const s = src.names[p.video] || {};
    return p.at == null ? '' : `<a class="ntime" href="#/note/${encodeURIComponent(p.video)}/${p.at}" style="--c:${NCOL[(s.i || 0) % NCOL.length]}" title="${esc((s.title || p.video) + (p.quote ? ' · “' + p.quote + '”' : ''))}">${esc(s.short || '')} f${p.at} (${tc(p.at, s.fps || 30)})</a>`; };
  return `<div class="ndive${A ? '' : ' wait'}"><div class="ndq"><svg class="i"><use href="#i-claude"/></svg><span class="grow">${esc(a.q)}</span>
      <span class="small dim">${esc(whenStr(a.made) || '')}</span><button type="button" class="btn sm ghost" data-unask="${esc(a.id)}" title="${ta('Remove this question')}">✕</button></div>
    ${A ? `<div class="nda"><div class="ndt">${esc(A.title)}</div><p>${esc(A.summary)}</p>
        <div class="ndl">${many ? t('From the videos') : t('From the video')}</div><ul class="nlist">${A.points.map(p => `<li>${esc(p.text)} ${chip(p)}</li>`).join('')}</ul>
        ${A.more ? `<div class="ndl more">${many ? t("Going further - Claude's own knowledge, not from the videos") : t("Going further - Claude's own knowledge, not from the video")}</div><div class="md">${md(A.more)}</div>` : ''}
        <div class="row" style="margin-top:8px"><button type="button" class="btn sm" data-dcopy="${i}"><svg class="i"><use href="#i-copy"/></svg>${t('Copy')}</button>
          ${claudeBtn(cmd, t('Answer it again'), 'notes', '', 'sm ghost')}</div></div>`
      : `<div class="ndw small muted">${t('Waiting for Claude - the answer shows here when it is saved.')} ${claudeBtn(cmd, t('Open Claude'), 'notes', '', 'sm cl')}</div>`}</div>`;
}
const noteDives = R => (R.asks || []).map((a, i) => diveHtml(a, i, `/take-notes ${R.name} ask ${a.id}`, {fps: R.fps})).join('')
  || `<div class="small dim">${t('No questions yet.')}</div>`;
function noteCard(n) {
  const when = strTime(n.created), N = n.notes;
  const st = n.status === 'ready' ? `<span class="small fnl grow ok">${t('✓ Notes ready')}</span>`
    : n.status === 'claude' ? `<span class="small fnl grow">${t('Waiting for Claude')}</span>${claudeBtn('/take-notes ' + n.name, t('Write the notes'), 'notes', n.name)}`
    : `<span class="small fnl grow bad">${t('No words or frames found')}</span>`;
  return `<div class="card pcard ncard"><a class="clink" href="#/note/${encodeURIComponent(n.name)}">
    <div class="ppic">${n.thumb ? `<img src="${fileUrl(n.thumb)}" loading="lazy" alt="">` : mascot('index', {size: 72, animated: false})}
      <span class="pbadges">${n.status === 'claude' ? `<span class="pbadge todo">${t('notes not written yet')}</span>` : ''}</span>
      ${when ? `<span class="pwhen" title="${esc(n.created || '')}">${esc(whenWords(when))}</span>` : ''}</div>
    <div class="cb"><span class="ct"${n.title && n.title !== n.label ? ` title="${esc(n.title)}"` : ''}>${esc(N && N.title || n.label)}</span><div class="small">${[lenWords(n.frames, n.fps), esc(n.uploader || ''), esc(n.platform || '')].filter(Boolean).join(' · ')}</div></div></a>
    ${N && N.tldr ? `<div class="small muted ntl2">${esc(N.tldr)}</div>` : ''}
    <div class="pfacts"><span>${N ? tn(N.takeaways, '<b>{n}</b> takeaway', '<b>{n}</b> takeaways') + (N.sections ? ' · ' + tn(N.sections, '<b>{n}</b> section', '<b>{n}</b> sections') : '')
      : n.transcript ? tn(n.transcript.words || 0, '{n} word heard', '{n} words heard') : ''}</span>${(n.tags || []).slice(0, 2).map(g => `<span class="tag dim">${esc(g)}</span>`).join(' ')}</div>
    <div class="cact">${st}</div>
    <span class="pdel">${delBtn('notes', n.name)}</span></div>`;
}
// Take notes: links (downloaded up to 720p - the user's pick) and / or videos already here, what the user wants from
// them, then by default ONE Claude window writes all their notes when the last one is ready (nothing to correct)
async function addNotesModal() {
  const [cands, ST] = await Promise.all([api('/api/candidates'), api('/api/settings')]);
  const cl = ST.tools.find(x => x.name === 'claude') || {}, yt = ST.tools.find(x => x.name === 'yt-dlp') || {};
  const fileRow = c => `<label class="avfile"><input type="checkbox" value="${esc(c.path)}">
    <span class="grow">${esc(c.name)}</span><span class="small dim">${c.size != null ? bytes(c.size) : ''}</span></label>`;
  modal(`<h2>${t('Take notes from videos')}</h2>
    <div class="avstep"><b>1</b><span>${t('Which videos?')}</span><span class="small muted">${t('up to {n} at a time - links are downloaded up to 720p', {n: AV_MAX})}</span></div>
    <textarea id="nvl" rows="3" placeholder="${ta('Paste links, one per line - YouTube, TikTok, Instagram, Vimeo…')}"></textarea>
    ${yt.found ? '' : `<div class="small amber">${t('Links need the downloader (yt-dlp): <a href="#/settings" onclick="closeModal()">Settings → Programs</a>. Files work without it.')}</div>`}
    <div class="small muted" style="margin:8px 0 4px">${t('or pick videos you already have (in the refs folder):')}</div>
    <div class="avfiles" id="nvfiles">${cands.map(fileRow).join('') || `<div class="small dim">${t('No videos in refs yet - paste a link, or the path of a video below.')}</div>`}</div>
    <div class="row" style="margin-top:6px">${browseBtn('nvbrowse')}<input type="text" id="nvpath" placeholder="${ta('…or the full path of a video elsewhere, e.g. C:\\Videos\\clip.mp4')}" style="flex:1"><button class="btn sm" id="nvadd" title="${ta('Adds the path in the box - with the box empty, it opens Browse')}">${t('Add')}</button></div>
    <div class="avstep opt"><b>2</b><span>${t('What do you want from it?')}</span>${optTag()}</div>
    <input type="text" id="nvask" maxlength="1000" style="width:100%" placeholder="${ta('e.g. how to apply it to my fitness channel, only the steps, the tools it names…')}">
    <div class="avstep"><b>3</b><span>${t("Claude's notes")}</span></div>
    <label class="chk avclaude"><input type="radio" name="nvc" value="1" ${cl.found ? 'checked' : 'disabled'}><span>${t('<b>Claude writes the notes when the words are ready</b> (recommended) - one Claude Code window for all of them, nothing for you to correct.')}${cl.found ? '' : ` <span class="bad">${t('Claude Code was not found - Settings.')}</span>`}</span></label>
    <label class="chk avclaude"><input type="radio" name="nvc" value="0" ${cl.found ? '' : 'checked'}><span>${t("<b>Only get the words and key frames</b> - ask Claude later from each video's page.")}</span></label>
    <details class="fold" style="margin-top:10px"><summary>${t('More options')}</summary><div class="in"><div class="form">
      <label for="nvtags">${t('Tags')} ${optTag()}</label><input type="text" id="nvtags" placeholder="${ta('e.g. pricing, freelance, editing')}"></div></div></details>
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="nvgo" disabled><svg class="i"><use href="#i-pen"/></svg>${t('Take notes')}</button>
      <span id="nvsum" class="small muted"></span></div>`, el => {
    const links = () => $('#nvl', el).value.split(/\s+/).map(x => x.trim()).filter(Boolean);
    const files = () => $$('#nvfiles input:checked', el).map(x => x.value);
    const upd = () => {
      const L = links(), F = files(), n = L.length + F.length, bad = L.filter(u => !/^https?:\/\/\S+$/i.test(u));
      $('#nvgo', el).disabled = !n || n > AV_MAX || bad.length > 0 || (L.length && !yt.found);
      $('#nvsum', el).innerHTML = bad.length ? `<span class="bad">${t('not a link: {link}', {link: esc(bad[0])})}</span>` : n > AV_MAX ? `<span class="bad">${t('at most {n} at a time', {n: AV_MAX})}</span>`
        : n ? [L.length ? tn(L.length, '{n} link (downloaded first)', '{n} links (downloaded first)') : '', F.length ? plural(F.length, 'file') : ''].filter(Boolean).join(' + ') : t('Paste a link or pick a video.');
    };
    $('#nvl', el).oninput = upd;
    $('#nvfiles', el).onchange = upd;
    const addPath = v => {                          // a video into the list, ticked (one already there is ticked again)
      const box = $('#nvfiles', el), had = $$('input', box).find(x => x.value === v);
      if (had) { had.checked = true; return; }
      const empty = box.querySelector('div.small.dim'); if (empty) empty.remove();
      box.insertAdjacentHTML('afterbegin', fileRow({path: v, name: v, size: null}));
      box.querySelector('input').checked = true;
    };
    const browse = () => pickVideos($('#nvbrowse', el), 'notes', addPath, upd);      // 2026-11-03: Browse… (home.js)
    $('#nvbrowse', el).onclick = browse;
    $('#nvadd', el).onclick = () => {
      const v = $('#nvpath', el).value.trim().replace(/^"|"$/g, '');
      if (!v) return browse();                                 // (an empty box: the picker)
      addPath(v); $('#nvpath', el).value = ''; upd();
    };
    $('#nvgo', el).onclick = async () => {
      const b = $('#nvgo', el); b.disabled = true;
      try {
        const r = await api('/api/notes/batch', {links: links(), files: files(), ask: $('#nvask', el).value, tags: $('#nvtags', el).value,
          claude: ($('input[name=nvc]:checked', el) || {}).value === '1'});
        closeModal(); ping();
        toast(tn(r.jobs.length, 'Taking notes from {n} video - follow it in the Analyser', 'Taking notes from {n} videos - follow them in the Analyser'), 'ok');
        if (location.hash !== '#/analyze/notes') location.hash = '#/analyze/notes'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    $('#nvl', el).focus();
    upd();
  }, 'wide');
}
// Combine notes (2026-10-29, the user: "multiple videos analized on the same topic ... combine the knowledge of the
// videos selected, or maybe create a markdown with all important info form both videos to maybe use it elsewhere or ask
// questions"): pick 2+ videos with notes -> one Markdown file (MotionLab, no Claude) or one question across them
// (ROOT\_combined\<id>.json, /take-notes combined <id>, its page #/notes-combined/<id>)
async function combineModal() {
  const all = (await api('/api/notes')).filter(n => n.status === 'ready');
  modal(`<h2>${t('Combine notes')}</h2>
    <div class="avstep"><b>1</b><span>${t('Which videos?')}</span><span class="small muted">${t('at least two - same topic works best')}</span></div>
    <div class="avfiles ncpick">${all.map(n => `<label class="avfile"><input type="checkbox" value="${esc(n.name)}">${n.thumb ? `<img src="${fileUrl(n.thumb)}" alt="" loading="lazy">` : ''}
      <span class="grow">${esc(n.notes && n.notes.title || n.label)}</span><span class="small dim">${esc(lenWords(n.frames, n.fps))}${(n.tags || []).length ? ' · ' + esc(n.tags.slice(0, 2).join(', ')) : ''}</span></label>`).join('')}</div>
    <div class="avstep"><b>2</b><span>${t('What do you want?')}</span></div>
    <div class="ncways"><div class="ncway"><b>${t('One Markdown file')}</b><span class="small muted">${t("Every video's notes, your own notes and one context block for another AI - made by MotionLab, no Claude.")}</span>
        <button class="btn" id="ncmd" disabled><svg class="i"><use href="#i-download"/></svg>${t('Download (.md)')}</button></div>
      <div class="ncway"><b>${t('Ask Claude across them')}</b><span class="small muted">${t('Claude reads every video and answers with each point tied to its video and moment.')}</span>
        <textarea id="ncq" rows="3" maxlength="2000">${esc(t('Combine what these videos teach into one set of notes: what they agree on, where they differ, and what to do first.'))}</textarea>
        <button class="btn cl" id="ncask" disabled><svg class="i"><use href="#i-claude"/></svg>${t('Ask Claude')}</button></div></div>`, el => {
    const names = () => $$('.ncpick input:checked', el).map(x => x.value);
    const upd = () => { const n = names().length; $('#ncmd', el).disabled = n < 2; $('#ncask', el).disabled = n < 2 || !$('#ncq', el).value.trim(); };
    $('.ncpick', el).onchange = upd; $('#ncq', el).oninput = upd;
    $('#ncmd', el).onclick = async () => {
      try {
        const r = await api('/api/notes-combined/md?names=' + encodeURIComponent(names().join(',')));
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([r.text], {type: 'text/markdown;charset=utf-8'})); a.download = r.file;
        document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        toast(t('Downloaded: {file}', {file: r.file}), 'ok');
      } catch (e) { toast(e.message, 'err'); }
    };
    $('#ncask', el).onclick = async () => {
      try {
        const rec = await api('/api/notes-combined/ask', {names: names(), q: $('#ncq', el).value});
        closeModal(); location.hash = '#/notes-combined/' + encodeURIComponent(rec.id);
        openClaude('/take-notes combined ' + rec.id, 'notes', 'combined');
      } catch (e) { toast(e.message, 'err'); }
    };
  }, 'wide');
}
async function pageCombined(main, id) {
  let R = await api('/api/notes-combined/' + encodeURIComponent(id));
  const src = () => ({names: Object.fromEntries(R.sources.map((s, i) => [s.name, {...s, i, short: String(i + 1).padStart(2, '0')}]))});
  const cmd = '/take-notes combined ' + R.id;
  const draw = () => {
    main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / <a href="#/analyze/notes">INDEX</a> / ${t('across videos')}</div>
      <div class="mtitle mhost">${mascot('index', {size: 46})}<h1>${esc(R.answer ? R.answer.title : t('A question across {n} videos', {n: R.names.length}))}</h1></div>
      <div class="sub">${esc(whenStr(R.made) || '')}</div></div>
      <div class="row">${R.answer ? `<button class="btn" id="ccopy"><svg class="i"><use href="#i-copy"/></svg>${t('Copy for another AI')}</button>` : ''}
        <button class="btn ghost" id="cdel"><svg class="i"><use href="#i-trash"/></svg>${t('Remove this question')}</button></div></div>
      <div class="ncsrc">${R.sources.map((s, i) => `<a class="ncs" style="--c:${NCOL[i % NCOL.length]}" href="${s.gone ? '#/analyze/notes' : '#/note/' + encodeURIComponent(s.name)}">
        <span class="nsn">${String(i + 1).padStart(2, '0')}</span>${s.thumb ? `<img src="${fileUrl(s.thumb)}" alt="">` : ''}<span class="grow">${esc(s.title || s.name)}${s.gone ? ` <span class="bad small">${t('(its notes were deleted)')}</span>` : ''}</span><span class="small dim">${esc(s.uploader || '')}</span></a>`).join('')}</div>
      <div class="ncmain">${diveHtml(R, 0, cmd, src())}</div>`;
    const c = $('#ccopy', main); if (c) c.onclick = () => copy(R.md);
    $$('[data-dcopy]', main).forEach(b => b.onclick = () => copy(R.md));
    const un = $('[data-unask]', main); if (un) un.remove();
    $('#cdel', main).onclick = async () => {
      try { await api('/api/notes-combined/remove', {id: R.id}); location.hash = '#/analyze/notes'; } catch (e) { toast(e.message, 'err'); }
    };
  };
  draw();
  let timer = 0;                                       // waiting for Claude: look again every 5 s
  const wait = () => { if (R.answer) return; timer = setTimeout(async () => {
    try { const NR = await api('/api/notes-combined/' + encodeURIComponent(id)); if (NR.answer) { R = NR; draw(); } } catch (e) { /* again */ }
    wait(); }, 5000); };
  onCleanup(() => clearTimeout(timer));
  wait();
}
// one video's notes (#/note/<name>): the notes on the left in one reading column - TL;DR, Key takeaways, the sections
// folded, Steps, Apply it (ticks), then Resources and Context for another AI folded; the video, My notes, the words and
// the key frames on the right. Every time = frame + timecode and moves the player; its quote on hover
async function pageNote(main, name, atF) {
  const R = await api('/api/notes/' + encodeURIComponent(name));
  const N = R.notes_full, fps = R.fps, inRefs = (R.video_rel || '').startsWith('refs/');
  const done = new Set(R.done || []);
  const head = `<div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / <a href="#/analyze/notes">INDEX</a> / ${t('notes')}</div>
      <div class="mtitle mhost">${mascot('index', {size: 46})}<h1${R.title && R.title !== R.label ? ` title="${esc(R.title)}"` : ''}>${esc(N && N.title || R.label)}</h1></div>
      <div class="sub">${[R.url ? `<a href="${esc(R.url)}" target="_blank" rel="noopener">${esc(R.platform || t('source'))}</a>` : '', esc(R.uploader || ''), lenWords(R.frames, fps),
        `${numStr(fps)} fps`, (R.tags || []).map(g => `<span class="tag dim">${esc(g)}</span>`).join(' ')].filter(Boolean).join(' · ')} <a href="#" id="nmeta" class="small">${t('edit')}</a></div></div>
    <div class="row">${N ? `<button class="btn" id="ndl"><svg class="i"><use href="#i-download"/></svg>${t('Download (.md)')}</button>
        <button class="btn" id="nctx"><svg class="i"><use href="#i-copy"/></svg>${t('Copy for another AI')}</button>` : ''}
      ${sparkLink(R.spark, R.video_there ? R.video : '')}
      <button class="btn" data-open="${esc(R.folder)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button>
      ${R.video_there && inRefs ? `<button class="btn ghost" data-del="notes_video" data-name="${esc(R.name)}" data-after="" title="${ta('The video goes to the Recycle Bin; the notes, your notes and the key frames stay')}"><svg class="i"><use href="#i-trash"/></svg>${t('Delete the video, keep the notes')}</button>` : ''}
      ${delBtn('notes', R.name, '#/analyze/notes', ' ' + t('Delete'))}</div></div>`;
  const ask = R.ask ? `<div class="small muted nask">${t('You asked for: {what}', {what: esc(R.ask)})}</div>` : '';
  let left;
  if (!N) {
    const T = R.transcript;
    left = `<div class="panel nwait mhost">${mascot('index', {size: 76})}<h2>${t('Claude has not written the notes yet')}</h2>
      <div class="small muted">${T ? t('MotionLab has the words ({words}, {source}) and {frames}.', {words: tn(T.words || 0, '{n} word', '{n} words'), source: esc(T.source === 'speech' ? t('heard by speech to text') : t("the platform's subtitles")), frames: tn(R.sheets.length, '{n} sheet of key frames', '{n} sheets of key frames')})
        : t('MotionLab found no words in this video - Claude works from its key frames.')}</div>
      ${(R.issues || []).map(x => `<div class="small dim" style="margin-top:4px">${esc(x)}</div>`).join('')}
      <div class="row" style="margin-top:12px">${claudeBtn('/take-notes ' + R.name, t('Write the notes with Claude'), 'notes', R.name, 'cl')}</div></div>${ask}`;
  } else {
    // 2026-10-29, the user: "present the information ... more structurally, kinda like Notion would", "make each
    // section ... more meaningful, maybe add some colors ... section dividing": one colour per section, carried by
    // its block, its piece of the map and every takeaway said inside it
    const secs = N.sections, L = R.frames;
    const ends = secs.map((s, i) => s.chapter != null && R.chapters[s.chapter] ? R.chapters[s.chapter].end : i + 1 < secs.length ? Math.max(s.at, secs[i + 1].at - 1) : L - 1);
    const secOf = f => f == null ? -1 : secs.findIndex((s, i) => f >= s.at && f <= ends[i]);
    const col = i => i < 0 ? 'var(--dim)' : NCOL[i % NCOL.length];
    const two = i => String(i + 1).padStart(2, '0');
    const pt = p => `<li>${esc(p.text)} ${nTime(p.at, fps, p.quote || '', p.replayed)}${p.shown != null && !p.quote ? `<span class="small dim"> ${t('(on screen)')}</span>` : ''}</li>`;
    const span = (a, b) => `${nTime(a, fps)}<span class="dim"> → </span><span class="ntc2">f${b} (${tc(b, fps)})</span>`;
    const T = R.transcript || {}, st = R.stats || {};
    const props = [[t('Type'), esc(NKIND[N.kind] || N.kind || '')], [t('Length'), esc(lenWords(R.frames, fps))], [t('Channel'), esc(R.uploader || '')],
      [t('Words'), T.words ? `${tn(T.words, '{n} word', '{n} words')} · ${esc(T.source === 'speech' ? t('heard by speech to text') : t("the platform's subtitles"))}${T.lang ? ` · ${esc(String(T.lang).toUpperCase())}` : ''}` : ''],
      [t('Views'), st.views != null ? numStr(st.views) : ''], [t('Notes by Claude'), esc(whenStr(N.made) || N.made || '')],
      [t('Done'), N.apply.length ? `<span id="nprogt">${done.size} / ${N.apply.length}</span>` : '']].filter(x => x[1]);
    const toc = [['ntl', 'TL;DR'], N.takeaways.length && ['ntake', t('Key takeaways')], secs.length && ['nsecs', t('Sections')], N.steps.length && ['nsteps', t('Steps')],
      N.apply.length && ['napp', t('Apply it')], ['nask', t('Ask Claude')], ['nmore', t('Context for another AI')]].filter(Boolean);
    const map = secs.length ? `<div class="nmap" id="nmap">${secs.map((s, i) => `<a href="#" class="nseg" data-f="${s.at}" style="--c:${col(i)};left:${(s.at / L * 100).toFixed(3)}%;width:${((ends[i] - s.at + 1) / L * 100).toFixed(3)}%" title="${esc(`${two(i)} ${s.title} · ${lenWords(ends[i] - s.at + 1, fps)}`)}"><span>${two(i)} ${esc(s.title)}</span></a>`).join('')}
        ${N.takeaways.filter(x => x.at != null).map(x => `<a href="#" class="ndot" data-f="${x.at}" style="left:${(x.at / L * 100).toFixed(3)}%" title="${esc(x.phrase)}"></a>`).join('')}<i class="nplay" id="nplay"></i></div>` : '';
    left = `<nav class="ntoc">${toc.map(([id, w]) => `<a href="#" data-go="${id}">${w}</a>`).join('')}</nav>
      <div class="nprops">${props.map(([k, v]) => `<div class="npk">${k}</div><div class="npv">${v}</div>`).join('')}</div>
      ${ask}${map}
      <div class="ntldr" id="ntl"><span class="ntk">TL;DR</span> ${esc(N.tldr)}</div>
      ${N.takeaways.length ? `<h2 class="nh" id="ntake">${t('Key takeaways')} <span class="ncount">${N.takeaways.length}</span></h2>
        <div class="ntkgrid">${N.takeaways.map((x, i) => { const k = secOf(x.at); return `<div class="ntkc" style="--c:${col(k)}"><div class="ntkn">${two(i)}</div>
          <b>${esc(x.phrase)}</b><p>${esc(x.text)}</p><div class="ntkf">${nTime(x.at, fps, x.quote || '', x.replayed)}${k >= 0 ? `<a href="#" class="nsecname" data-go="nsec${k}">${esc(secs[k].title)}</a>` : ''}</div></div>`; }).join('')}</div>` : ''}
      ${secs.length ? `<h2 class="nh" id="nsecs">${t('Sections')} <span class="ncount">${secs.length}</span></h2>
        ${secs.map((s, i) => `<details class="nsb" open id="nsec${i}" style="--c:${col(i)}"><summary><span class="nsn">${two(i)}</span>
          <span class="nsh"><span class="nst">${esc(s.title)}</span>${s.gist ? `<span class="nsg">${esc(s.gist)}</span>` : ''}</span>
          <span class="nsr"><span>${span(s.at, ends[i])}</span><span class="small dim">${esc(lenWords(ends[i] - s.at + 1, fps))} · ${tn(s.points.length, '{n} point', '{n} points')} · ${((ends[i] - s.at + 1) / L * 100).toFixed(0)} %</span></span></summary>
          <ul class="nlist nsp">${s.points.map(pt).join('')}</ul></details>`).join('')}` : ''}
      ${N.steps.length ? `<h2 class="nh" id="nsteps">${t('Steps')} <span class="ncount">${N.steps.length}</span></h2>
        <ol class="nstepl">${N.steps.map((s, i) => `<li style="--c:${col(secOf(s.at))}"><span class="nstn">${i + 1}</span><div>${esc(s.text)} ${nTime(s.at, fps, s.quote || '', s.replayed)}</div></li>`).join('')}</ol>` : ''}
      ${N.apply.length ? `<h2 class="nh" id="napp">${t('Apply it')} <span class="nprog"><i id="nprogb" style="width:${(done.size / N.apply.length * 100).toFixed(0)}%"></i></span></h2>
        <div class="napply">${N.apply.map((a, i) => `<label class="chk${done.has(i) ? ' done' : ''}"><input type="checkbox" data-ap="${i}" ${done.has(i) ? 'checked' : ''}><span>${esc(a)}</span></label>`).join('')}</div>` : ''}
      <div class="naskp" id="nask"><h2 class="nh">${mascot('index', {size: 26, animated: false})} ${t('Ask Claude about this video')}</h2>
        <div class="small muted">${t("Go deeper on a part, turn it into a plan, ask what it means for you. Claude answers from the video's words - each point plays its moment - and keeps what it adds from its own knowledge apart.")}</div>
        <div class="nsugg">${[t('Explain the main idea in more depth, with examples'), t('Turn this into a plan I can follow this week'), t('How would I apply this to my own content?'),
          ...secs.slice(0, 6).map(s => t('Go deeper on "{part}"', {part: s.title}))].map(q => `<button type="button" class="nchip" data-q="${esc(q)}">${esc(q)}</button>`).join('')}</div>
        <div class="row nqrow"><textarea id="nq2" rows="2" maxlength="2000" placeholder="${ta('Ask anything about this video…')}"></textarea>
          <button class="btn cl" id="nqgo" disabled><svg class="i"><use href="#i-claude"/></svg>${t('Ask Claude')}</button></div>
        <div id="ndives">${noteDives(R)}</div>
        ${(R.combined || []).length ? `<div class="small muted" style="margin-top:10px">${t('Also asked across videos:')} ${R.combined.map(c => `<a href="#/notes-combined/${encodeURIComponent(c.id)}">${esc(c.q.length > 70 ? c.q.slice(0, 70) + '…' : c.q)}</a>`).join(' · ')}</div>` : ''}</div>
      ${N.resources.length ? `<details class="fold"><summary>${tn(N.resources.length, 'Resources ({n} link from the description)', 'Resources ({n} links from the description)')}</summary><div class="in"><ul class="nlist">${N.resources.map(r => `<li><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a> <span class="small dim">${esc(r.url)}</span></li>`).join('')}</ul></div></details>` : ''}
      <details class="fold" id="nmore"><summary>${t('Context for another AI')}</summary><div class="in"><pre class="nctx">${esc(N.ai_context)}</pre>
        <button class="btn sm" id="nctx2"><svg class="i"><use href="#i-copy"/></svg>${t('Copy')}</button></div></details>
      <div class="small dim nfoot">${t("Notes by Claude · {when} · every point is tied to the video's own words or a frame it shows", {when: esc(whenStr(N.made) || N.made || '')})}
        · ${claudeBtn('/take-notes ' + R.name, t('Write them again'), 'notes', R.name, 'sm ghost')}</div>`;
  }
  const player = R.video_rel ? `<video id="nvid" controls preload="metadata" src="${fileUrl(R.video_rel)}"></video>`
    : `<div class="nnovid">${R.thumb ? `<img src="${fileUrl(R.thumb)}" alt="">` : ''}<div class="small muted">${R.video_there ? t('This video sits outside the lab folder, so it plays in its own folder only.') : t('The video was deleted - the notes stay.')}</div></div>`;
  main.innerHTML = `${head}<div class="ngrid"><div class="nnotes">${left}</div>
    <div class="nside">${player}
      <div class="ntabs"><button data-nt="mine" class="on">${t('My notes')}</button><button data-nt="words">${t('Transcript')}</button>${R.sheets.length ? `<button data-nt="frames">${t('Key frames')}</button>` : ''}</div>
      <div data-np="mine"><textarea id="nmine" placeholder="${ta('Your own notes - what you think, what you will try. Markdown works: # heading, - list, **bold**.')}">${esc(R.mine_text || '')}</textarea>
        <div class="small dim" id="nmst">${t('saved with the notes and in the download')}</div></div>
      <div data-np="words" hidden>${R.lines.length ? `<input type="search" id="nq" placeholder="${ta('Search the words…')}" style="width:100%">
          <div class="nlines" id="nlines">${R.lines.map((l, i) => `<div class="nline" data-i="${i}" data-f="${l.start}"><span class="ntc">f${l.start} (${tc(l.start, fps)})</span> ${esc(l.text)}</div>`).join('')}</div>`
        : `<div class="small muted">${t('No words in this video.')}</div>`}</div>
      <div data-np="frames" hidden><div class="nsheets">${R.sheets.map((s, i) => `<img src="${fileUrl(s)}" data-i="${i}" loading="lazy" alt="">`).join('')}</div></div>
    </div></div>`;
  sparkWire(main);
  const vid = $('#nvid', main);
  const seek = f => { if (!vid) return; vid.currentTime = (+f + 0.5) / fps; vid.play().catch(() => {}); };
  $('.ngrid', main).addEventListener('click', e => {
    const g = e.target.closest('[data-go]');
    if (g) { e.preventDefault(); const x = document.getElementById(g.dataset.go); if (x) { if (x.tagName === 'DETAILS') x.open = true; x.scrollIntoView({behavior: 'smooth', block: 'start'}); } return; }
    const a = e.target.closest('.ntime, .nline, .nseg, .ndot');
    if (!a || a.getAttribute('href') && a.getAttribute('href').startsWith('#/')) return;
    e.preventDefault(); seek(a.dataset.f);
  });
  if (vid && atF != null) vid.addEventListener('loadedmetadata', () => seek(atF), {once: true});   // #/note/<name>/<frame>
  const play = $('#nplay', main);
  if (vid && play) vid.addEventListener('timeupdate', () => { play.style.left = `${(vid.currentTime * fps / R.frames * 100).toFixed(2)}%`; play.hidden = false; });
  if (N) {
    const q2 = $('#nq2', main), go = $('#nqgo', main), box = $('#ndives', main);
    q2.oninput = () => { go.disabled = !q2.value.trim(); };
    $$('.nchip', main).forEach(c => c.onclick = () => { q2.value = c.dataset.q; q2.focus(); q2.oninput(); });
    const redrawDives = () => { box.innerHTML = noteDives(R); };
    go.onclick = async () => {
      go.disabled = true;
      try {
        const rec = await api(`/api/notes/${encodeURIComponent(R.name)}/ask`, {q: q2.value});
        R.asks = [{...rec, md: ''}, ...(R.asks || [])]; redrawDives(); q2.value = '';
        openClaude(`/take-notes ${R.name} ask ${rec.id}`, 'notes', R.name);
        waitDives();
      } catch (err) { toast(err.message, 'err'); go.disabled = false; }
    };
    box.addEventListener('click', async e => {
      const u = e.target.closest('[data-unask]'), c = e.target.closest('[data-dcopy]');
      if (c) { copy(R.asks[+c.dataset.dcopy].md || ''); return; }
      if (!u) return;
      try { await api(`/api/notes/${encodeURIComponent(R.name)}/unask`, {id: u.dataset.unask}); R.asks = R.asks.filter(a => a.id !== u.dataset.unask); redrawDives(); }
      catch (err) { toast(err.message, 'err'); }
    });
    // a question waiting for Claude: look again every 5 s (only this list, never the page - the video keeps playing)
    let timer = 0;
    const waitDives = () => {
      clearTimeout(timer);
      if (!(R.asks || []).some(a => !a.answer)) return;
      timer = setTimeout(async () => {
        try {
          const NR = await api('/api/notes/' + encodeURIComponent(R.name));
          if (JSON.stringify((NR.asks || []).map(a => [a.id, !!a.answer])) !== JSON.stringify(R.asks.map(a => [a.id, !!a.answer]))) { R.asks = NR.asks; redrawDives(); }
        } catch (err) { /* try again */ }
        waitDives();
      }, 5000);
    };
    onCleanup(() => clearTimeout(timer));
    waitDives();
  }
  $$('.ntabs button', main).forEach(b => b.onclick = () => {
    $$('.ntabs button', main).forEach(x => x.classList.toggle('on', x === b));
    $$('[data-np]', main).forEach(p => { p.hidden = p.dataset.np !== b.dataset.nt; });
  });
  $$('.nsheets img', main).forEach(im => im.onclick = () => lightbox(R.sheets.map((s, i) => ({src: s, cap: t('Key frames, sheet {n}', {n: i + 1})})), +im.dataset.i));
  const q = $('#nq', main), lines = $$('.nline', main);
  if (q) q.oninput = () => { const s = q.value.toLowerCase(); lines.forEach((d, i) => { d.hidden = !!s && !R.lines[i].text.toLowerCase().includes(s); }); };
  if (vid && lines.length) {
    let last = -1;
    vid.ontimeupdate = () => {                       // the line being said is marked while the video plays
      const f = Math.floor(vid.currentTime * fps);
      let k = -1;
      for (let i = 0; i < R.lines.length && R.lines[i].start <= f; i++) if (f <= R.lines[i].end) k = i;
      if (k === last) return;
      if (last >= 0 && lines[last]) lines[last].classList.remove('sel');
      if (k >= 0 && lines[k]) lines[k].classList.add('sel');
      last = k;
    };
  }
  const mine = $('#nmine', main), mst = $('#nmst', main);
  let sent = R.mine_text || '';
  const saveMine = async () => {
    const v = mine.value;
    if (v === sent) return;
    try { await api(`/api/notes/${encodeURIComponent(R.name)}/mine`, {text: v}); sent = v; mst.textContent = t('saved ✓'); mst.className = 'small ok'; }
    catch (e) { mst.textContent = t('NOT saved: {err}', {err: e.message}); mst.className = 'small bad'; }
  };
  const later = debounce(saveMine, 600);
  mine.oninput = () => { mst.textContent = t('saving…'); mst.className = 'small dim'; later(); };
  mine.onblur = saveMine;
  onCleanup(() => { if (mine.value !== sent) saveMine(); });
  $$('[data-ap]', main).forEach(c => c.onchange = async () => {
    c.closest('label').classList.toggle('done', c.checked);
    const ticks = $$('[data-ap]', main).filter(x => x.checked).map(x => +x.dataset.ap);
    const pb = $('#nprogb', main), pt = $('#nprogt', main);
    if (pb) pb.style.width = `${(ticks.length / N.apply.length * 100).toFixed(0)}%`;
    if (pt) pt.textContent = `${ticks.length} / ${N.apply.length}`;
    try { await api(`/api/notes/${encodeURIComponent(R.name)}/meta`, {done: ticks}); } catch (e) { toast(e.message, 'err'); }
  });
  const ctx = () => copy(`${t('Context from the video "{title}"', {title: N.title || R.label})}${R.url ? ` (${R.url})` : ''}:\n\n${N.ai_context}`);
  const c1 = $('#nctx', main); if (c1) c1.onclick = ctx;
  const c2 = $('#nctx2', main); if (c2) c2.onclick = ctx;
  const dl = $('#ndl', main);
  if (dl) dl.onclick = () => modal(`<h2>${t('Download the notes')}</h2>
      <p class="small muted">${t("One Markdown file (.md): Claude's notes and your own - it opens in Notion, Obsidian, Google Docs or any text editor.")}</p>
      <label class="chk"><input type="checkbox" id="ndtr"><span>${t('with the whole transcript (frame + timecode per line)')}</span></label>
      <div class="row" style="margin-top:14px"><button class="btn pri" id="ndgo"><svg class="i"><use href="#i-download"/></svg>${t('Download (.md)')}</button><button class="btn" id="ndno">${t('Cancel')}</button></div>`, el => {
    $('#ndno', el).onclick = closeModal;
    $('#ndgo', el).onclick = async () => {
      try {
        if (mine.value !== sent) await saveMine();
        const r = await api(`/api/notes/${encodeURIComponent(R.name)}/md${$('#ndtr', el).checked ? '?transcript=1' : ''}`);
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([r.text], {type: 'text/markdown;charset=utf-8'})); a.download = r.file;
        document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        closeModal(); toast(t('Downloaded: {file}', {file: r.file}), 'ok');
      } catch (e) { toast(e.message, 'err'); }
    };
  });
  $('#nmeta', main).onclick = e => {
    e.preventDefault();
    modal(`<h2>${t('Name and tags')}</h2><div class="form"><label for="nml">${t('Name')}</label><input type="text" id="nml" maxlength="120" value="${esc(R.label || '')}">
      <label for="nmt">${t('Tags')}</label><input type="text" id="nmt" value="${esc((R.tags || []).join(', '))}" placeholder="${ta('e.g. pricing, freelance, editing')}"></div>
      <div class="row" style="margin-top:14px"><button class="btn pri" id="nmgo">${t('Save')}</button><button class="btn" id="nmno">${t('Cancel')}</button></div>`, el => {
      $('#nmno', el).onclick = closeModal;
      $('#nmgo', el).onclick = async () => {
        try { await api(`/api/notes/${encodeURIComponent(R.name)}/meta`, {label: $('#nml', el).value, tags: $('#nmt', el).value}); closeModal(); route(); }
        catch (err) { toast(err.message, 'err'); }
      };
    });
  };
}
