/* MotionLab app - js/analyser-sets.js: the analysed videos' progress, thumbnail sets, Preview your thumbnail, scripts & prompts sets.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ videos (analyses)
const FOCUS_SHORT = {content: t('Content'), cinematic: t('Cinematic'), both: t('Content + cinematic')};
const focusChip = f => f ? `<span class="fchip sm focus-${esc(f)}" title="${ta('what Claude looked at')}">${esc(FOCUS_SHORT[f] || f)}</span>` : '';
// the lines a card shows for its focus (profile.py: the hook / talking / text; the signature effects / transitions)
const focusLines = r => { const L = r.lines || {}, f = r.focus || 'both';
  return [f !== 'cinematic' && L.content, f !== 'content' && L.cinematic, f !== 'content' && L.colour].filter(Boolean)
    .map(x => `<div class="small muted pline">${esc(x)}</div>`).join(''); };
// Analyze > in progress: the downloads and analyses running or waiting their turn (queued jobs) - refreshed every 2 s
// while any is active. A finished one shows for 5 s, then it is gone; a failed one stays until its ✕ (the user,
// 2026-10-15: "Done ... showing all the time? make it a 5 s pop up and then it disappears forever, or a discard
// option"). The ✕'d ones are remembered in this browser (by number + start: the numbers restart with the app).
const DONE_SHOW_S = 5;
const jobKey = j => `${j.id}@${j.started}`;
const GONE_JOBS = new Set((() => { try { return JSON.parse(localStorage.getItem('ml.goneJobs') || '[]'); } catch (e) { return []; } })());
const hideJob = k => { GONE_JOBS.add(k); try { localStorage.setItem('ml.goneJobs', JSON.stringify([...GONE_JOBS].slice(-200))); } catch (e) { /* this session only */ } };
function progressPanel(el, onEnd, kinds = ['download', 'analyze'], match = () => true) {
  let stop = false, last = '', was = new Set(), timer = null;      // was = the jobs active at the last tick
  const word = s => ({queued: t('waiting|job'), running: t('running|job'), cancelling: t('cancelling|job'), done: t('done|job'),
                      failed: t('failed|job'), cancelled: t('cancelled|job')})[s] || s;   // a job's state on its tag
  const tick = async () => {
    if (stop) return;
    clearTimeout(timer);
    let list = [];
    try { list = (await api('/api/jobs')).filter(j => kinds.includes(j.kind) && match(j)); } catch (e) { /* the next tick */ }
    const act = list.filter(j => j.status === 'running' || j.status === 'queued' || j.status === 'cancelling')
      .sort((a, b) => (a.status === 'queued') - (b.status === 'queued') || a.id - b.id);   // running first, then in turn
    const ended = list.filter(j => !act.includes(j) && j.ended_ago_s != null && !GONE_JOBS.has(jobKey(j)));
    const fresh = ended.filter(j => j.status !== 'failed' && j.ended_ago_s < DONE_SHOW_S);
    const recent = [...ended.filter(j => j.status === 'failed' && j.ended_ago_s < 900), ...fresh].slice(0, 4);
    const sig = act.map(j => j.id + j.status).join() + '|' + recent.map(j => j.id + j.status).join();
    const now = new Set(act.map(j => j.id));
    if ([...was].some(id => !now.has(id))) onEnd();     // one ended (a download that queued its analysis too)
    was = now;
    if (sig !== last) {
      last = sig;
      const bad = recent.some(j => j.status === 'failed');
      el.innerHTML = act.length || recent.length ? `<div class="panel progress"><div class="row sp"><h2>${act.length ? t('Working on {jobs}', {jobs: plural(act.length, 'job')}) : bad ? t('Something went wrong') : t('Done|jobs')}</h2><a class="small" href="#/jobs">${t('all jobs')} →</a></div>
        ${[...act, ...recent].map(j => `<div class="pjob ${esc(j.status)}"><span class="tag ${esc(j.status)}">${esc(word(j.status))}</span>
          <span class="grow">${esc(j.title)}${j.then ? ` <span class="small dim">${j.then_kind === 'notes' ? t('→ then its notes') : t('→ then analysed')}</span>` : ''}${j.then_claude ? ` <span class="small amber">${j.kind === 'notes' ? t('→ then Claude writes the notes') : t('→ then Claude checks it')}</span>` : ''}</span>
          <a class="small" href="#/jobs/${j.id}">${t('log|job')}</a>${j.status === 'queued' ? `<button class="btn sm ghost" data-cancel="${j.id}">${t('Remove')}</button>` : ''}${j.status === 'failed' ? reportBtn(j.id, 'sm ghost') : ''}
          ${recent.includes(j) ? `<button class="btn sm ghost icon" data-hide="${esc(jobKey(j))}" title="${ta('Hide')}">✕</button>` : ''}</div>`).join('')}</div>` : '';
      $$('[data-cancel]', el).forEach(b => b.onclick = async () => { try { await api(`/api/jobs/${b.dataset.cancel}/cancel`, {}); tick(); } catch (e) { toast(e.message, 'err'); } });
      $$('[data-hide]', el).forEach(b => b.onclick = () => { hideJob(b.dataset.hide); last = ''; tick(); });
    }
    if (act.length) timer = setTimeout(tick, 2000);
    else if (fresh.length) timer = setTimeout(tick, (DONE_SHOW_S - Math.max(...fresh.map(j => j.ended_ago_s))) * 1000 + 150);
  };
  tick();
  return () => { stop = true; clearTimeout(timer); };
}
// Analyze > Downloaded, not analysed yet: one row per file; the files of one post (an Instagram carousel, a TikTok
// photo post with its sound - 0.4.2.1, downloads.json "post") under one heading, in their order
const waitKind = w => w.photo ? 'photo' : w.audio ? 'audio' : 'video';
const waitWord = w => ({photo: t('photo'), audio: t('audio'), video: t('video')})[waitKind(w)];   // the kind on its tag
const waitRow = (w, part = '') => `<tr class="${part ? 'postpart' : ''}">
  <td>${part ? `<span class="small dim">${part}</span> ` : ''}<span class="tag">${waitWord(w)}</span></td><td><b>${esc(part ? w.name.replace(/ \[[^\]]+\]\.\w+$/, '') || w.name : w.title || w.name)}</b><div class="small dim mono">${esc(w.name)}</div></td>
  <td class="small muted">${w.url && !part ? `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.platform || t('link'))}</a> · ` : ''}${esc(w.modified)}</td><td class="num small">${bytes(w.size)}</td>
  <td class="row" style="justify-content:flex-end">${w.photo ? `<span class="small dim">${t('a photo of the post')}</span>` : w.audio ? `<span class="small dim">${part ? t("the post's sound") : t('music for an edit (Editor)')}</span>` : `<button class="btn sm pri" data-an="${esc(w.path)}">${t('Analyze…')}</button>`}${delBtn('file', w.rel, '', ' ' + t('Delete'))}</td></tr>`;
function waitRows(wait) {
  const groups = [];
  wait.forEach(w => { const g = w.post && groups.find(x => x.post === w.post); if (g) g.items.push(w); else groups.push({post: w.post || null, items: [w]}); });
  return groups.map(g => {
    if (!g.post) return waitRow(g.items[0]);
    const f = g.items[0], n = f.parts || g.items.length, kinds = {};
    g.items.forEach(w => { kinds[waitKind(w)] = (kinds[waitKind(w)] || 0) + 1; });
    const gone = n - g.items.length;                 // parts analysed or deleted since
    return `<tr class="posthead"><td><span class="tag post">${t('post')}</span></td><td><b>${esc(f.title || f.name)}</b>
        <div class="small dim">${t('one post, {parts}: {kinds}', {parts: plural(n, 'part'), kinds: Object.entries(kinds).map(([k, c]) => plural(c, k)).join(', ')})}${gone > 0 ? ' ' + tn(gone, '({n} analysed or removed)', '({n} analysed or removed)') : ''}</div></td>
      <td class="small muted"><a href="${esc(g.post)}" target="_blank" rel="noopener">${esc(f.platform || t('link'))}</a> · ${esc(f.modified)}</td>
      <td class="num small">${bytes(g.items.reduce((a, w) => a + w.size, 0))}</td><td></td></tr>`
      + g.items.map(w => waitRow(w, t('part {part} of {n}', {part: w.part, n}))).join('');
  }).join('');
}
// Analyser > the downloads nobody analysed (0.4.3.5, the user: "make it a little row that says X pending videos ...
// and if clicked u go to that list" - the analysed videos come first, like the Editor)
function waitingModal(wait) {
  const vids = wait.filter(w => !w.photo && !w.audio);
  modal(`<h2>${t('Downloaded, not analysed yet')}</h2>
    <div class="small muted" style="margin-top:-4px">${wait.length > vids.length ? t('Videos you downloaded and did not analyse yet, and music or photos from your downloads. Analyse one, or delete what you do not need (it goes to the Recycle Bin).')
      : t('Videos you downloaded and did not analyse yet. Analyse one, or delete what you do not need (it goes to the Recycle Bin).')}</div>
    ${vids.length > 1 ? `<div class="row" style="margin-top:12px"><button class="btn pri" id="wall"><svg class="i"><use href="#i-analyze"/></svg>${vids.length > AV_MAX ? t('Analyse the first {n}…', {n: AV_MAX}) : t('Analyse all {n}…', {n: vids.length})}</button></div>` : ''}
    <div class="waiting" style="margin-top:12px"><table class="t"><tbody>${waitRows(wait)}</tbody></table></div>`, el => {
    $$('[data-an]', el).forEach(b => b.onclick = () => { closeModal(); addVideosModal({files: [b.dataset.an], pick: true}); });
    const all = $('#wall', el); if (all) all.onclick = () => { closeModal(); addVideosModal({files: vids.slice(0, AV_MAX).map(w => w.path), pick: true}); };
  }, 'wide');
}
// one analysis as a card like the Editor's (0.4.3.5): a frame with the date it was analysed, the name, the length; the
// rhythm in one line; the next step with its button
// ---- thumbnail sets (0.4.5, the user: "I give 15 thumbnails from mr beast, it analyzes them and then sees common
// patterns like font, color, structure ... then that information can be used when im generating thumbnails"):
// analysis\thumbs\<set> (motionlab\thumbsets.py): the pictures only (no video), measured by the lab; Claude's
// /analyze-reference thumbs <set> writes the patterns (style.json); the user marks each one; Ready to post uses them
const THUMBS_JOBS = ['thumbs_fetch', 'thumbs_links', 'thumbs_measure', 'thumbs_more', 'thumbs_refresh', 'thumbs_fontmatch'];
// a set's pictures in order (the user, 2026-10-15: "add some filters like most viewed or less viewed ... and some data
// to the card like the date"): # = as added; views; date (YouTube's "3 weeks ago" = an approximate date, ≈)
const TS_SORTS = [['n', '#'], ['views_d', t('Most viewed|thumbnails')], ['views_a', t('Least viewed|thumbnails')], ['date_d', t('Newest|thumbnails')],
  ['date_a', t('Oldest|thumbnails')]];
// newest / oldest: the place in the channel's listing first (exact), else the date (a picture from a link)
const tsDay = it => Date.parse(it.upload_date || '') || 0;
const tsSortCmp = {n: (a, b) => a.n - b.n, views_d: (a, b) => (b.views ?? -1) - (a.views ?? -1), views_a: (a, b) => (a.views ?? Infinity) - (b.views ?? Infinity),
  date_d: (a, b) => (a.pos != null && b.pos != null ? a.pos - b.pos : tsDay(b) - tsDay(a)),
  date_a: (a, b) => (a.pos != null && b.pos != null ? b.pos - a.pos : (tsDay(a) || Infinity) - (tsDay(b) || Infinity))};
const tsSorted = (items, k) => items.slice().sort((a, b) => tsSortCmp[k](a, b) || a.n - b.n);
const COMPACT = LANG === 'en' ? null : new Intl.NumberFormat(LANG, {notation: 'compact', maximumFractionDigits: 1});   // 1,2 mil
const compactNum = v => COMPACT ? COMPACT.format(v) : v >= 1e9 ? `${+(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${Math.round(v / 1e3)}K` : String(v);
// an exact date as a date; an approximate one (YouTube's "3 weeks ago" read back) in the same words, not a false day
const AGO = {day: n => tn(n, '≈ {n} day ago', '≈ {n} days ago'), week: n => tn(n, '≈ {n} week ago', '≈ {n} weeks ago'),
  month: n => tn(n, '≈ {n} month ago', '≈ {n} months ago'), year: n => tn(n, '≈ {n} year ago', '≈ {n} years ago')};
const dayWords = (d, approx) => { const m = /^(\d{4})-(\d\d)-(\d\d)$/.exec(d || ''); if (!m) return '';
  if (!approx) return `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}`;
  const days = Math.max(0, Math.round((Date.now() - Date.UTC(+m[1], +m[2] - 1, +m[3])) / 864e5));
  const [n, w] = days < 14 ? [days, 'day'] : days < 60 ? [Math.round(days / 7), 'week'] : days < 365 ? [Math.round(days / 30), 'month'] : [Math.round(days / 365), 'year'];
  return n === 0 ? t('≈ today') : AGO[w](n); };
const lenOf = s => s == null ? '' : s >= 3600 ? `${Math.floor(s / 3600)}:${pad(Math.floor(s % 3600 / 60))}:${pad(Math.round(s % 60))}` : `${Math.floor(s / 60)}:${pad(Math.round(s % 60))}`;
let TS_SORT = 'n';
const setSlug = s => String(s || '').normalize().replace(/[^\p{L}\p{N}_\-. ]+/gu, '_').trim().replace(/\s+/g, '_')
  .replace(/\.{2,}/g, '_').replace(/_{2,}/g, '_').replace(/^[_. ]+|[_. ]+$/g, '').slice(0, 80);
const hexOk = c => /^#[0-9a-f]{6}$/i.test(String(c || ''));
function setCard(s) {                               // s.label = the user's own name for the set (shown as it is)
  const tm = strTime(s.updated);
  return `<div class="card pcard setcard">${newTag(`ts:${s.name}@${Math.round(s.created || 0)}`, s.created)}<a class="clink" href="#/thumbs/${encodeURIComponent(s.name)}">
    <div class="ppic">${s.cover ? `<img src="${fileUrl(s.cover)}" loading="lazy" alt="">` : '<svg class="ic"><use href="#i-thumb"/></svg>'}
      <span class="pbadges">${s.has_style ? '' : `<span class="pbadge todo" title="${ta('Claude has not looked at them yet')}">${t('patterns not found yet')}</span>`}</span>
      ${tm ? `<span class="pwhen">${esc(whenWords(tm))}</span>` : ''}</div>
    <div class="cb"><span class="ct">${esc(s.label)}</span><div class="small">${s.channel_total ? t('{thumbnails} <span class="muted">of {total} on the channel</span>', {thumbnails: plural(s.count, 'thumbnail'), total: numStr(s.channel_total)})
      : plural(s.count, 'thumbnail')}${s.measured < s.count ? ' · ' + tn(s.measured, '{n} measured', '{n} measured') : ''}</div></div></a>
    <div class="pfacts"><span class="fchip sm">${t('Thumbnail set')}</span>${s.has_style ? `<span class="small ok">${t('✓ patterns found')}</span>` : ''}</div>
    <span class="pdel">${delBtn('thumbs', s.name)}</span></div>`;
}
// ---- Preview your thumbnail (2026-10-24, the user: "upload ur thumbnails and have it like a test on a fake generated
// yotubue page (updated if possible) like a preview layout thumnbail to see if the thumnbail matches the vibe or pops
// from a normal youtube user feed"): a full-window copy of today's YouTube layouts - Home grid, Search, the Up next
// column, a phone - with the user's pictures among big channels' newest, most viewed videos (then: "besides big
// youtubers like mrbeast ... probably of highly viewed recent videos" - motionlab\thumbfeed.py, the job thumb_feed,
// *Channels…* = the list) or the real thumbnails of the sets analysed here (GET /api/thumbtest: their titles, channels,
// views, lengths), and ones made in MotionLab (Ready to post). Dark / light, Shuffle, Squint (a blur: what still reads
// is what pops), Where is mine? Nothing is saved: the pictures stay in this window.
function thumbTest() {
  const o = document.createElement('div'); o.className = 'yttest';
  const T = {mine: [], layout: 'home', theme: 'dark', blur: false, set: '', seed: 1, pool: [], made: [], sets: [], big: {}, busy: false, edit: false};
  const cf = new Intl.NumberFormat(LANG === 'es' ? 'es-ES' : 'en-US', {notation: 'compact', maximumFractionDigits: 1});
  const views = n => t('{n} views', {n: cf.format(n || 0)});
  const AGES = [[1, 'hour'], [5, 'hour'], [1, 'day'], [3, 'day'], [1, 'week'], [2, 'week'], [3, 'week'], [1, 'month'], [4, 'month'], [1, 'year']];
  const ago = k => { const [n, u] = AGES[k % AGES.length];
    return u === 'hour' ? tn(n, '{n} hour ago', '{n} hours ago') : u === 'day' ? tn(n, '{n} day ago', '{n} days ago')
      : u === 'week' ? tn(n, '{n} week ago', '{n} weeks ago') : u === 'month' ? tn(n, '{n} month ago', '{n} months ago') : tn(n, '{n} year ago', '{n} years ago'); };
  const dur = s => { s = Math.round(+s || 0); if (!s) return ''; const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60;
    return h ? `${h}:${pad(m)}:${pad(x)}` : `${m}:${pad(x)}`; };
  const rnd = k => { let x = Math.sin(T.seed * 9301 + k * 49297) * 233280; return x - Math.floor(x); };
  const HUES = [4, 28, 48, 140, 190, 215, 265, 300, 330];
  const avatar = (name, k) => `<span class="ytav" style="background:hsl(${HUES[(name || '?').charCodeAt(0) % HUES.length]} 55% ${T.theme === 'dark' ? 38 : 58}%)">${esc((name || '?').trim().charAt(0).toUpperCase())}</span>`;
  // the feed: the pool (one set or all), shuffled by the seed, the user's pictures put among the first ones seen
  const feed = (n, shift = 0) => {
    const pool = T.pool.filter(x => !T.set || x.set === T.set).map((x, i) => ({...x, k: i})).sort((a, b) => rnd(a.k) - rnd(b.k));
    const items = [];
    for (let i = 0; i < n; i++) items.push(pool.length ? {...pool[i % pool.length], k: i} : {k: i, blank: true});
    const slots = [1, 6, 9, 3, 11, 4].map(s => (s + shift + Math.floor(rnd(97) * 3)) % Math.max(n, 1));
    T.mine.forEach((m, j) => { const at = slots[j % slots.length]; items.splice(at, 0, {...m, mine: true, k: 1000 + j}); });
    return items.slice(0, Math.max(n, T.mine.length));
  };
  const med = () => { const v = T.pool.map(x => x.views).filter(Boolean).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : 12000; };
  const meta = x => x.mine ? `${views(med())} · ${ago(2)}` : `${views(x.views)} · ${ago(x.k + Math.floor(rnd(x.k) * 4))}`;
  const pic = (x, cls = '') => x.blank ? `<span class="ytpic blank ${cls}"></span>`
    : `<span class="ytpic ${cls}${x.mine ? ' mine' : ''}"><img src="${esc(x.src || fileUrl(x.img))}" alt="" loading="lazy">${x.duration || x.mine ? `<i class="ytdur">${x.mine ? esc(x.len || '8:24') : dur(x.duration)}</i>` : ''}${!x.mine && rnd(x.k + 7) > 0.86 ? `<b class="ytwatched" style="width:${Math.round(20 + rnd(x.k) * 70)}%"></b>` : ''}</span>`;
  const title = x => x.blank ? '<span class="ytline"></span><span class="ytline short"></span>' : esc(x.title || t('Your video title'));
  const chan = x => x.blank ? '' : esc(x.channel || '');
  const VIEWS = {
    home: () => `<div class="ytchips">${[t('All'), t('Music'), t('Gaming'), t('Live'), t('Podcasts'), t('Recently uploaded'), t('New to you')].map((c, i) => `<span class="${i ? '' : 'on'}">${c}</span>`).join('')}</div>
      <div class="ytgrid">${feed(12).map(x => `<div class="ytcard">${pic(x)}<div class="ytinfo">${x.blank ? '<span class="ytav"></span>' : avatar(x.channel, x.k)}<div><b>${title(x)}</b><span>${chan(x)}</span><span>${x.blank ? '' : meta(x)}</span></div></div></div>`).join('')}</div>`,
    search: () => `<div class="ytsearch">${feed(6).map(x => `<div class="ytrow">${pic(x, 'big')}<div class="ytrinfo"><b>${title(x)}</b><span>${x.blank ? '' : meta(x)}</span>
        <span class="ytrch">${x.blank ? '' : avatar(x.channel, x.k)}${chan(x)}</span><span class="ytsnip">${x.blank ? '' : esc(t('Watch it to the end - the best part is the last minute.'))}</span></div></div>`).join('')}</div>`,
    upnext: () => { const L = feed(11, 2), first = L.find(x => !x.mine) || {blank: true};
      return `<div class="ytwatch"><div class="ytplayer">${first.blank ? '' : `<img src="${esc(first.src || fileUrl(first.img))}" alt="">`}<span class="ytbar"><i></i></span></div>
        <b class="ytwtitle">${title(first)}</b><div class="ytrch">${first.blank ? '' : avatar(first.channel, 0)}${chan(first)}</div></div>
        <div class="ytside">${L.filter(x => x !== first).slice(0, 10).map(x => `<div class="ytsrow">${pic(x, 'small')}<div><b>${title(x)}</b><span>${chan(x)}</span><span>${x.blank ? '' : meta(x)}</span></div></div>`).join('')}</div>`; },
    phone: () => `<div class="ytphone"><div class="ytpbar"><span class="ytlogo"><i></i>YouTube</span></div>${feed(6).map(x => `<div class="ytpcard">${pic(x)}<div class="ytinfo">${x.blank ? '<span class="ytav"></span>' : avatar(x.channel, x.k)}<div><b>${title(x)}</b><span>${x.blank ? '' : `${chan(x)} · ${meta(x)}`}</span></div></div></div>`).join('')}</div>`};
  const LAYOUTS = [['home', t('Home')], ['search', t('Search')], ['upnext', t('Up next')], ['phone', t('Phone')]];
  const draw = () => {
    const q = T.layout === 'search' ? (T.mine[0] || {}).title || '' : '';
    o.innerHTML = `<div class="yttools"><b class="yttt"><svg class="i"><use href="#i-thumb"/></svg>${t('Preview your thumbnail')}</b>
        <label class="btn sm pri"><svg class="i"><use href="#i-upload"/></svg>${t('Add your thumbnail…')}<input type="file" hidden multiple accept="image/*,.heic,.avif"></label>
        ${T.made.length ? `<select class="ytmade"><option value="">${t('Or one made in MotionLab…')}</option>${T.made.map((m, i) => `<option value="${i}">${esc(m.video)} · ${esc(m.img.split('/').pop())}</option>`).join('')}</select>` : ''}
        <span class="grow"></span>
        <div class="seg ytseg">${LAYOUTS.map(([k, l]) => `<button data-lay="${k}" class="${T.layout === k ? 'on' : ''}">${l}</button>`).join('')}</div>
        <div class="seg ytseg"><button data-th="dark" class="${T.theme === 'dark' ? 'on' : ''}">${t('Dark')}</button><button data-th="light" class="${T.theme === 'light' ? 'on' : ''}">${t('Light')}</button></div>
        <select class="ytset" title="${ta('The videos around yours')}"><option value="_big" ${T.set === '_big' ? 'selected' : ''}>${t('Big creators - newest, most viewed')}</option>${T.sets.map(s => `<option value="${esc(s.name)}" ${T.set === s.name ? 'selected' : ''}>${esc(s.label)}</option>`).join('')}<option value="" ${T.set === '' ? 'selected' : ''}>${t('All of them')}</option></select>
        <button class="btn sm${T.blur ? ' on' : ''}" data-blur title="${ta('Blurs the page: what you can still read from a distance is what pops')}">${t('Squint')}</button>
        <button class="btn sm" data-shuf>${t('Shuffle')}</button><button class="btn sm" data-where ${T.mine.length ? '' : 'disabled'}>${t('Where is mine?')}</button>
        <button class="btn sm" data-x>${t('Close')}</button></div>
      <div class="ytmine">${T.mine.map((m, i) => `<span class="ytm"><img src="${esc(m.src)}" alt=""><input type="text" data-mt="${i}" value="${esc(m.title)}" placeholder="${ta('Your video title')}"><input type="text" data-mc="${i}" value="${esc(m.channel)}" placeholder="${ta('Your channel')}" class="ytmc"><button data-mrm="${i}" title="${ta('Take it out')}">✕</button></span>`).join('')}
        ${T.mine.length ? '' : `<span class="small muted">${t('Add one or more of your thumbnails (16:9) - they show up among the others. Nothing is saved: the pictures stay in this window.')}</span>`}
        <span class="grow"></span>${feedLine()}</div>${T.edit ? chanEditor() : ''}
      <div class="ytpage yt-${T.theme}${T.blur ? ' blur' : ''} ytl-${T.layout}"><div class="ythead"><span class="ytburger"><i></i><i></i><i></i></span><span class="ytlogo"><i></i>YouTube</span>
          <span class="ytq"><span>${esc(q) || t('Search')}</span><i></i></span><span class="ytme">${avatar((T.mine[0] || {}).channel || '?', 0)}</span></div>
        <div class="ytbody yt-${T.layout}">${VIEWS[T.layout]()}</div></div>`;
    const inp = $('input[type=file]', o);
    inp.onchange = () => { [...inp.files].forEach(f => T.mine.push({src: URL.createObjectURL(f), title: f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '), channel: T.me || t('You'), url: true})); inp.value = ''; draw(); };
    const mk = $('.ytmade', o); if (mk) mk.onchange = () => { const m = T.made[+mk.value]; if (m) T.mine.push({src: fileUrl(m.img), title: m.title, channel: T.me || t('You')}); draw(); };
    const ss = $('.ytset', o); if (ss) ss.onchange = () => { T.set = ss.value; draw(); };
    const gf = $('[data-getfeed]', o); if (gf) gf.onclick = getFeed;
    const ce = $('[data-chans]', o); if (ce) ce.onclick = () => { T.edit = !T.edit; draw(); };
    const cs = $('[data-chsave]', o); if (cs) cs.onclick = async () => {
      try { const r = await api('/api/thumbfeed/channels', {channels: $('.ytchans textarea', o).value.split('\n')});
        T.big.channels = r.channels; T.edit = false; getFeed(); } catch (e) { toast(e.message, 'err'); } };
    const cr = $('[data-chreset]', o); if (cr) cr.onclick = async () => {
      try { const r = await api('/api/thumbfeed/channels', {channels: []}); T.big.channels = r.channels; draw(); } catch (e) { toast(e.message, 'err'); } };
    $$('[data-lay]', o).forEach(b => b.onclick = () => { T.layout = b.dataset.lay; draw(); });
    $$('[data-th]', o).forEach(b => b.onclick = () => { T.theme = b.dataset.th; draw(); });
    $('[data-blur]', o).onclick = () => { T.blur = !T.blur; draw(); };
    $('[data-shuf]', o).onclick = () => { T.seed++; draw(); };
    $('[data-where]', o).onclick = () => { $$('.ytpic.mine', o).forEach(p => { p.classList.add('flash'); setTimeout(() => p.classList.remove('flash'), 1600); }); };
    $('[data-x]', o).onclick = close;
    const retitle = debounce(() => draw(), 600);
    $$('[data-mt]', o).forEach(x => x.oninput = () => { T.mine[+x.dataset.mt].title = x.value; retitle(); });
    $$('[data-mc]', o).forEach(x => x.oninput = () => { T.mine[+x.dataset.mc].channel = x.value; retitle(); });
    $$('[data-mrm]', o).forEach(b => b.onclick = () => { const [m] = T.mine.splice(+b.dataset.mrm, 1); if (m.url) URL.revokeObjectURL(m.src); draw(); });
    o.ondragover = e => e.preventDefault();
    o.ondrop = e => { e.preventDefault(); [...e.dataTransfer.files].filter(f => /^image\//.test(f.type) || /\.(heic|avif)$/i.test(f.name))
      .forEach(f => T.mine.push({src: URL.createObjectURL(f), title: f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '), channel: T.me || t('You'), url: true})); draw(); };
  };
  // big channels' newest videos: what the feed holds, Get the newest videos (the job thumb_feed, followed here), Channels…
  const feedLine = () => { const B = T.big || {};
    return T.busy ? `<span class="small amber">${t('Getting the newest videos of big channels…')}</span>`
      : `<span class="small muted">${B.count ? t('{n} videos of big channels · {when}', {n: B.count, when: esc(B.fetched || '')}) : t('No videos of big channels yet')}</span>
        ${!B.count || B.stale ? `<button class="btn sm pri" data-getfeed title="${ta('Lists the newest videos of big channels and downloads their thumbnails - no video is downloaded')}">${t('Get the newest videos')}</button>` : ''}
        <button class="btn sm ghost" data-chans>${t('Channels…')}</button>`; };
  const chanEditor = () => `<div class="ytchans"><span class="small muted">${t('The channels the feed comes from, one per line (@handle or a channel link):')}</span>
      <textarea rows="6">${esc((T.big.channels || []).join('\n'))}</textarea><div class="row"><button class="btn sm pri" data-chsave>${t('Save and get their videos')}</button>
      <button class="btn sm ghost" data-chreset>${t('Back to the usual ones')}</button></div></div>`;
  const load = async () => { const r = await api('/api/thumbtest'); T.pool = r.pool || []; T.made = r.made || []; T.sets = r.sets || []; T.big = r.big || {}; return r; };
  const getFeed = async () => {
    let j;
    try { j = await api('/api/jobs', {kind: 'thumb_feed', args: {}, queue: true}); } catch (e) { toast(e.message, 'err'); return; }
    T.busy = true; draw();
    for (;;) {
      await new Promise(r => setTimeout(r, 2000));
      if (!o.isConnected) return;
      let s; try { s = await api(`/api/jobs/${j.id}?since=0`); } catch (e) { continue; }
      if (['running', 'queued', 'cancelling'].includes(s.status)) continue;
      T.busy = false;
      if (s.status !== 'done') toast(t('Could not get the newest videos: {why}', {why: (s.log || []).slice(-1)[0] || s.status}), 'err');
      try { await load(); if (T.big.count) T.set = '_big'; } catch (e) { /* the old feed */ }
      draw(); return;
    }
  };
  const key = e => { if (e.key === 'Escape' && !/^(INPUT|SELECT|TEXTAREA)$/.test((document.activeElement || {}).tagName)) { e.preventDefault(); e.stopPropagation(); close(); } };
  const close = () => { T.mine.forEach(m => m.url && URL.revokeObjectURL(m.src)); o.remove(); window.removeEventListener('keydown', key, true); };
  window.addEventListener('keydown', key, true);
  document.body.append(o);
  o.innerHTML = `<div class="loading">${t('Loading…')}</div>`;
  Promise.all([load(), api('/api/settings').catch(() => ({}))]).then(([r, S]) => {
    T.me = ((S.settings || {}).author || '').replace(/-/g, ' ');
    T.set = T.big.count || !T.sets.length ? '_big' : '';
    draw();
    if (!T.big.count || T.big.stale) getFeed();                    // the first look: fetch them at once
  }).catch(e => { toast(e.message, 'err'); close(); });
}
// a picture the user picked or dropped -> the set (a raw body, like Film it's uploads; the server copies it in)
function uploadThumb(set, file) {
  return fetch(`/api/thumbs/${encodeURIComponent(set)}/upload?name=${encodeURIComponent(file.name)}`,
    {method: 'POST', headers: {'X-ML-Token': TOKEN, 'Content-Type': 'application/octet-stream'}, body: file})
    .then(async r => { const j = await r.json().catch(() => ({})); if (!r.ok || j.error) throw new Error(j.error || r.statusText); return j; });
}
async function addThumbsModal(pre = {}) {
  const ST = await api('/api/settings'), yt = ST.tools.find(x => x.name === 'yt-dlp') || {};
  const st = {from: 'channel', n: '15', order: 'newest'}, files = [];
  modal(`<h2>${pre.set ? t('Add more thumbnails') : t('Analyze thumbnails')}</h2>
    <div class="small muted" style="margin-top:-4px">${t("Only the pictures, their titles and views are kept - no video is downloaded, and they stay on this PC. Then Claude finds what they have in common: the text, the font's style, the colours, the structure.")}</div>
    ${pre.set ? '' : `<div class="avstep"><b>1</b><span>${t('Name the set')}</span></div><input type="text" id="tsname" placeholder="${ta('e.g. MrBeast')}" maxlength="60" style="max-width:320px">`}
    <div class="avstep"><b>${pre.set ? 1 : 2}</b><span>${t('From where?')}</span></div>
    <div class="seg" id="tsfrom"><button data-v="channel">${t('A channel or playlist')}</button><button data-v="links">${t('Some videos')}</button><button data-v="files">${t('Pictures you have')}</button></div>
    <div class="tsf" data-f="channel"><input type="text" id="tsurl" placeholder="https://www.youtube.com/@MrBeast" style="width:100%">
      <div class="row small" style="margin-top:8px">${t('start with')} <div class="seg" id="tsn">${['10', '15', '20', '30'].map(v => `<button data-v="${v}">${v}</button>`).join('')}</div>
        <div class="seg" id="tsord"><button data-v="newest">${t('the newest|thumbnails')}</button><button data-v="views">${t('the most viewed|thumbnails')}</button></div></div>
      <div class="small muted" style="margin-top:6px">${t("MotionLab lists the whole channel (a few seconds) - add more from the set's page whenever you want. Claude reads them 15 to a sheet, so a bigger set takes Claude longer.")}</div></div>
    <div class="tsf" data-f="links"><textarea id="tslinks" rows="4" placeholder="${ta('One video link per line')}" style="width:100%"></textarea></div>
    <div class="tsf" data-f="files"><label class="tsdrop" id="tsdrop"><input type="file" id="tsfiles" accept=".jpg,.jpeg,.png,.webp" multiple hidden>
      <span>${t('Drop pictures here or <b>choose them</b> (.jpg .png .webp) - copies go into the set, your files stay where they are')}</span></label><div class="small muted" id="tsflist"></div></div>
    ${yt.found ? '' : `<div class="small amber" style="margin-top:6px">${t('Links need the downloader (yt-dlp): Settings → Programs. Your own pictures work without it.')}</div>`}
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="tsgo" disabled><svg class="i"><use href="#i-thumb"/></svg>${t('Add the thumbnails')}</button><span class="small muted" id="tssum"></span></div>`, el => {
    const nameOf = () => pre.set || setSlug($('#tsname', el).value);
    const links = () => $('#tslinks', el).value.split(/\s+/).map(x => x.trim()).filter(Boolean);
    const upd = () => {
      $$('.tsf', el).forEach(x => x.hidden = x.dataset.f !== st.from);
      const url = $('#tsurl', el).value.trim(), L = links();
      const ready = nameOf() && (st.from === 'channel' ? /^https?:\/\/\S+$/i.test(url) && yt.found
        : st.from === 'links' ? L.length && L.every(u => /^https?:\/\/\S+$/i.test(u)) && yt.found : files.length);
      $('#tsgo', el).disabled = !ready;
      $('#tssum', el).textContent = !nameOf() ? t('Name the set first.') : st.from === 'files' ? (files.length ? plural(files.length, 'picture') : '') : '';
      $('#tsflist', el).textContent = files.map(f => f.name).join(' · ');
    };
    spSeg(el, '#tsfrom', st, 'from', upd); spSeg(el, '#tsn', st, 'n'); spSeg(el, '#tsord', st, 'order');
    ['#tsurl', '#tslinks'].forEach(s => $(s, el).oninput = upd);
    const nm = $('#tsname', el); if (nm) { nm.oninput = upd; nm.focus(); }
    const addF = list => { for (const f of list) if (/\.(jpe?g|png|webp)$/i.test(f.name) && !files.some(x => x.name === f.name && x.size === f.size)) files.push(f); upd(); };
    $('#tsfiles', el).onchange = e => { addF(e.target.files); e.target.value = ''; };
    const dz = $('#tsdrop', el);
    dz.ondragover = e => { e.preventDefault(); dz.classList.add('on'); };
    dz.ondragleave = () => dz.classList.remove('on');
    dz.ondrop = e => { e.preventDefault(); dz.classList.remove('on'); addF(e.dataTransfer.files); };
    $('#tsgo', el).onclick = async () => {
      const b = $('#tsgo', el), set = nameOf(), label = pre.set ? '' : $('#tsname', el).value.trim();
      b.disabled = true;
      try {
        if (st.from === 'files') {
          for (let i = 0; i < files.length; i++) { $('#tssum', el).textContent = t('copying {i} of {n}…', {i: i + 1, n: files.length}); await uploadThumb(set, files[i]); }
          closeModal(); toast(tn(files.length, '{n} picture added and measured', '{n} pictures added and measured'), 'ok');
          location.hash = '#/thumbs/' + encodeURIComponent(set);
          return;
        }
        const args = st.from === 'channel' ? {set, url: $('#tsurl', el).value.trim(), n: +st.n, order: st.order, label} : {set, urls: links()};
        await api('/api/jobs', {kind: st.from === 'channel' ? 'thumbs_fetch' : 'thumbs_links', args, queue: true});
        closeModal(); ping();
        toast(t('Getting the thumbnails - the set shows in the Analyser when they are in'), 'ok');
        if (location.hash !== '#/analyze/thumbs') location.hash = '#/analyze/thumbs'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    upd();
  }, 'wide');
}
// one set (the user, 2026-10-15: "make 'What they have in common' a dropdown or pop up so they dont take up all space
// of the page ... i also want to look at the thumbnails while reviewing them"): the pictures in the main column; beside
// them a side panel with Claude's patterns that stays in view while the pictures scroll and folds away (◂ / ▸) - a
// click on a pattern lights up its example pictures; under the pictures the lab's own numbers, folded and labelled
// "MotionLab · no Claude" (the user: "be clear that it is only MotionLab NOT Claude"). Since 2026-10-18 the side panel
// is the one review panel (reviewPanel): Is Claude right? per pattern + a note, the count live, Send it to Claude =
// the patterns again with your verdicts (the skill reads verdicts.json first)
let TS_FOLD = false, TS_STOP = null;
async function pageThumbs(main, name) {
  const S = await api('/api/thumbs/' + encodeURIComponent(name));
  const ch = S.channel;                                // the whole channel listed once (0.4.5): its size, what is left
  const st = S.style, V = S.verdicts || {}, items = S.items || [], sm = S.summary || {}, enc = encodeURIComponent(S.name);
  const nf = v => numLoc(Number(v));
  const pats = (st && st.patterns) || [], f = (st && st.font) || {};
  // 0.4.6: the font, measured - the words Claude listed (style.json "texts") against the font library, by shape
  const FM = S.fontmatch, pct = x => Math.round((x || 0) * 100) + ' %';
  const pick = String(((st || {}).for_make || {}).font || (f.closest || [])[0] || '');     // Claude's first choice
  const guess = FM && pick && (FM.ranking || []).find(r => pick.startsWith(r.family));
  const fmRow = !st ? '' : FM && FM.best ? kvRow(t('Font, measured'), `<span class="mlchip sm" title="${ta('MotionLab compared the words on the pictures with every font it has, letter by letter - Claude only said where the words are')}">MotionLab</span>
      <b>${esc(FM.best.family)}</b> ${esc(FM.best.weight)} <span class="muted">· ${t('matches {pct} over {texts}, the best on {n}', {pct: pct(FM.best.score), texts: plural(FM.best.items, 'text'), n: FM.best.first_on})}</span>
      ${FM.best.runner_up ? `<div class="small muted">${t('then {font} {pct}', {font: esc(FM.best.runner_up.family), pct: pct(FM.best.runner_up.score)})}${guess && guess.family !== FM.best.family ? ' · ' + t("Claude's guess {font} {pct}", {font: esc(guess.family), pct: pct(guess.score)}) : ''}</div>` : ''}
      <button class="btn sm ghost" id="tsfm" title="${ta('again, e.g. after you added a font (about 2 seconds, no Claude)')}">${t('Measure again')}</button>`)
    : (st.texts || []).length ? kvRow(t('Font, measured'), `<button class="btn sm" id="tsfm" title="${ta('the words Claude listed against every font MotionLab has, letter by letter (about 2 seconds, no Claude)')}">${t('Measure the font')}</button>`) : '';
  // what Claude found besides the patterns (under the panel's rows): the font, measured and named, colours, words, structure
  const facts = !st ? '' : `<div class="kv tskv">
        ${fmRow}
        ${f.style ? kvRow(FM && FM.best ? t("Font's style") : t('Font'), `${esc(f.style)}${(f.closest || []).length ? ` <span class="dim">- ${t('closest: {fonts}', {fonts: f.closest.map(esc).join(', ')})}</span>` : ''}${f.sure === false ? ` <span class="dim">${t('(a guess from the pictures)')}</span>` : ''}`) : ''}
        ${(st.colours || []).filter(hexOk).length ? kvRow(t('Colours'), st.colours.filter(hexOk).map(c => `<span class="swatch" style="background:${c}" title="${c}"></span>`).join('')) : ''}
        ${st.words ? kvRow(t('Words'), `${t('{avg} on average, at most {max}', {avg: numStr(st.words.median ?? '?'), max: numStr(st.words.max ?? '?')})}${st.words.case ? ' · ' + esc(st.words.case) : ''}`) : ''}
        ${(st.structures || []).length ? kvRow(t('Structure'), st.structures.map(s => `${esc(s.name)} (${esc(s.count)})`).join(' · ')) : ''}</div>
      <div class="small muted" style="margin-top:10px">${t('Use it in a video: <i>Ready to post</i> → Make a thumbnail yourself → <b>In the style of {name}</b>.', {name: esc(S.label || S.name)})}</div>`;
  const side = st ? '' : `<div class="row sp tsside-h"><h2>${t('What they have in common')}</h2><span class="clchip">Claude</span>
        <button class="btn sm ghost icon" id="tsfold" title="${ta('Fold it away')}">◂</button></div>
      <div class="small muted">${t("Claude has not looked at this set yet. It reads the numbered pictures and names what repeats - the text, the font's style, the colours, the structure, the faces - so <i>Ready to post</i> can make your thumbnails in this style.")}</div>`;
  const many = plural(items.length, 'thumbnail');
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / <a href="#/analyze/thumbs">${t('Thumbnails')}</a> / ${t('thumbnail set')}</div><h1>${esc(S.label || S.name)}</h1>
      <div class="sub">${ch && ch.total ? t('{thumbnails} of the {total} videos of {who}', {thumbnails: many, total: numStr(ch.total), who: esc(ch.who || t('the channel'))})
        : (S.source || {}).url ? t('{thumbnails} from {url}', {thumbnails: many, url: esc(S.source.url)}) : many}${S.updated ? ` · ${esc(whenStr(S.updated))}` : ''}</div></div>
      <div class="row">${delBtn('thumbs', S.name, '#/analyze/thumbs', t('Delete'))}</div></div>
    <div class="toprow">${claudeBtn(`/analyze-reference thumbs ${S.name}`, st ? t('Find the patterns again') : t('Find the patterns with Claude'), 'review', `thumbs ${S.name}`, st ? 'big tsfind' : 'pri big')}
      ${ch && ch.left !== 0 ? `<button class="btn big" id="tsnext" title="${ta('The next ones of {who} that are not in the set yet', {who: ch.who || t('the channel')})}"><svg class="i"><use href="#i-download"/></svg>${t('More from the channel')}${ch.left ? ` <span class="small muted">· ${tn(ch.left, '{n} left', '{n} left')}</span>` : ''}</button>` : ''}
      <button class="btn${ch && ch.left !== 0 ? '' : ' big'}" id="tsmore"><svg class="i"><use href="#i-thumb"/></svg>${t('Add more')}</button>
      <span class="grow"></span><button class="btn ghost" id="tsopen"${TS_FOLD ? '' : ' hidden'}>${t('What they have in common')} ▸</button></div>
    <div id="tsprog"></div>
    <div class="tslayout${TS_FOLD ? ' folded' : ''}">
      <div class="tsmain">
        <details class="panel tsmeas"><summary><h2>${t('Measured by MotionLab')}</h2><span class="mlchip" title="${ta("the app's own numbers, measured from the pictures - Claude was not involved")}">${t('MotionLab · no Claude')}</span>
          <span class="small muted">${t('colours, brightness, faces, where the text sits - numbers only')}</span></summary>
          ${(sm.colours || []).length ? `<div class="row" style="gap:6px;margin:10px 0 6px">${sm.colours.filter(c => hexOk(c.hex)).map(c => `<span class="swatch big" style="background:${c.hex}" title="${esc(tn(c.pictures, '{word} {hex} - in {n} pictures', '{word} {hex} - in {n} pictures', {word: t(c.word || ''), hex: c.hex}))}"></span>`).join('')}</div>` : ''}
          <ul class="tslines">${(S.lines || []).filter(l => !/^Claude's style|^Font, measured/.test(l)).map(l => `<li>${esc(l)}</li>`).join('')}</ul></details>
        <div class="row tssort"><span class="small muted">${t('Sort')}</span><div class="seg" id="tssort">${TS_SORTS.map(([k, l]) => `<button data-v="${k}">${l}</button>`).join('')}</div>
          <span class="grow"></span>${ch ? `<button class="btn sm ghost" id="tsrefresh" title="${ta('The channel listed again (seconds, nothing downloaded): the newest views, the dates, the lengths')}">${t('Update the views and dates')}</button>` : ''}</div>
        <div class="tsgrid">${tsSorted(items, TS_SORT).map(it => `<figure class="tscell" data-n="${it.n}"><img src="${fileUrl(it.path)}" loading="lazy" alt="">
          <figcaption><div class="tsct"><b>#${it.n}</b> ${esc(it.title || '')}</div>
            <div class="tscd">${[it.views != null ? `<span title="${esc(tn(it.views, '{n} views', '{n} views', {n: nf(it.views)}))}">${tn(it.views, '{n} views', '{n} views', {n: compactNum(it.views)})}</span>` : '',
              it.outperformer != null ? `<span class="${it.outperformer >= 1 ? 'ok' : ''}" title="${ta("views ÷ the channel's followers")}">${numStr(it.outperformer)}x</span>` : '',
              it.upload_date ? `<span title="${it.date_approx ? ta('about - YouTube only says how long ago') : ta('published')}">${dayWords(it.upload_date, it.date_approx)}</span>` : '',
              it.duration != null ? `<span title="${ta("the video's length")}">${lenOf(it.duration)}</span>` : ''].filter(Boolean).join('<i>·</i>') || `<span class="dim">${t('your picture')}</span>`}</div></figcaption>
          <button class="btn sm ghost icon tsrm" data-n="${it.n}" title="${ta('Take #{n} out of the set', {n: it.n})}">✕</button></figure>`).join('')}</div>
      </div>
      <aside class="${st ? '' : 'panel '}tsside" id="tsside">${side}</aside>
    </div>`;
  // a pattern lights up its example pictures (the current row of the panel; a second click lets it go)
  const light = pid => {
    const p = pats.find(x => x.id === pid), ex = new Set(p ? (p.examples || []).map(String) : []);
    $$('.tscell', main).forEach(c => { c.classList.toggle('hl', ex.has(c.dataset.n)); c.classList.toggle('dimmed', !!p && !ex.has(c.dataset.n)); });
    const first = p && $(`.tscell[data-n="${[...ex][0]}"]`, main);
    if (first) first.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  };
  const post = rvQueue();
  if (st) reviewPanel($('#tsside', main), {
    title: `${t('What they have in common')} <span class="clchip" title="${ta('written by Claude from the numbered pictures')}">Claude</span>`,
    head: `<button class="btn sm ghost icon" id="tsfold" title="${ta('Fold it away - the pictures take the whole width')}">◂</button>`,
    top: st.summary ? `<details class="tssum"><summary class="small muted">${t('In short')} <span class="dim">· ${t('click to read')}</span></summary><p>${esc(st.summary)}</p></details>` : '',
    sections: [{id: 'patterns', ask: t('Is Claude right?'), intro: t('Click a pattern to light up its pictures, then say if it is really there.'), scale: 'claims', note: 'line',
      items: () => pats.map(p => ({id: p.id, label: `<span class="fchip sm">${esc(p.kind || '')}</span> <b>${esc(p.what || '')}</b>`,
        sub: `${esc(p.how_many || '')}${(p.examples || []).length ? ` · #${p.examples.map(esc).join(' #')}` : ''}`})),
      get: pid => V[pid] || {},
      set: (pid, a) => {                            // verdicts.json, one home - the note too since 2026-10-18
        const note = a.note.trim(), body = {patterns: {[pid]: {v: a.v, note}}};
        if (a.v || note) V[pid] = {v: a.v, note}; else delete V[pid];
        return post(() => api(`/api/thumbs/${enc}/verdicts`, body));
      },
      empty: t('Claude named no pattern in this set.')}],
    extra: {panel: facts}, start: false, deselect: true, onMove: (s, pid) => light(pid),
    send: {hint: t('Claude looks at the patterns again with your verdicts: it keeps the ones you marked correct and fixes or drops the rest.'),
      cmd: `/analyze-reference thumbs ${S.name}`, task: 'review', name: `thumbs ${S.name}`}});
  const lay = $('.tslayout', main);
  const fold = on => { TS_FOLD = on; lay.classList.toggle('folded', on); $('#tsopen', main).hidden = !on; };
  $('#tsfold', main).onclick = () => fold(true);
  $('#tsopen', main).onclick = () => fold(false);
  $('#tsmore', main).onclick = () => addThumbsModal({set: S.name});
  const sortSt = {sort: TS_SORT};
  spSeg(main, '#tssort', sortSt, 'sort', () => {        // the cards move; nothing is asked again
    TS_SORT = sortSt.sort;
    const grid = $('.tsgrid', main), cell = Object.fromEntries($$('.tscell', grid).map(c => [c.dataset.n, c]));
    tsSorted(items, TS_SORT).forEach(it => cell[it.n] && grid.appendChild(cell[it.n]));
  });
  const rf = $('#tsrefresh', main);
  if (rf) rf.onclick = async () => { rf.disabled = true;
    try { await api('/api/jobs', {kind: 'thumbs_refresh', args: {set: S.name}, queue: true}); ping(); } catch (e) { toast(e.message, 'err'); rf.disabled = false; } };
  const nx = $('#tsnext', main); if (nx) nx.onclick = () => moreThumbsModal(S, () => pageThumbs(main, S.name));
  const fmb = $('#tsfm', main);
  if (fmb) fmb.onclick = async () => { fmb.disabled = true;
    try { await api('/api/jobs', {kind: 'thumbs_fontmatch', args: {set: S.name}, queue: true}); ping(); } catch (e) { toast(e.message, 'err'); fmb.disabled = false; } };
  if (TS_STOP) TS_STOP();                             // the page's own progress: getting more, measuring - then redraw
  TS_STOP = progressPanel($('#tsprog', main), () => pageThumbs(main, S.name), THUMBS_JOBS, j => (j.args || {}).set === S.name);
  onCleanup(() => { if (TS_STOP) { TS_STOP(); TS_STOP = null; } });
  $$('.tsrm', main).forEach(b => b.onclick = async () => {
    try { await api(`/api/thumbs/${enc}/remove`, {n: +b.dataset.n}); pageThumbs(main, S.name); } catch (e) { toast(e.message, 'err'); }
  });
}
// More from the channel (the user, 2026-10-15: "if i have 100 thumbnails available for clavero or 150 for mrbeast and
// i already got 10, 20 i could choose to download other 20/30 batch"): the next n not in the set - the newest or the
// most viewed - from the listing the set keeps (asked for again when a day old); job thumbs_more
function moreThumbsModal(S, after) {
  const ch = S.channel, known = ch.left != null, st = {n: String(known ? Math.min(20, ch.left) : 20), order: 'newest'};
  const sizes = known ? [10, 20, 30, 50].filter(v => v < ch.left).map(String).concat([String(Math.min(ch.left, 100))]) : ['10', '20', '30', '50'];
  modal(`<h2>${t('More from {name}', {name: esc(ch.who || S.label || S.name)})}</h2>
    <div class="small muted" style="margin-top:-4px">${known ? t("{in_set} of the channel's {total} videos are in this set - {left} left.", {in_set: numStr(ch.in_set), total: numStr(ch.total), left: numStr(ch.left)}) : t('{n} are in this set - MotionLab lists the whole channel first (a few seconds).', {n: numStr(ch.in_set)})} ${t('Only their thumbnails, titles and views - no video.')}</div>
    <div class="avstep"><b>1</b><span>${t('How many?')}</span></div><div class="seg" id="tmn">${[...new Set(sizes)].map(v => `<button data-v="${v}">${known && +v === ch.left ? t('all {n}', {n: v}) : v}</button>`).join('')}</div>
    <div class="avstep"><b>2</b><span>${t('Which ones?')}</span></div>
    <div class="seg" id="tmo"><button data-v="newest">${t('the newest not in the set')}</button><button data-v="views">${t('the most viewed not in the set')}</button></div>
    <div class="small muted" id="tmsum" style="margin-top:12px"></div>
    <div class="row" style="margin-top:12px"><button class="btn pri big" id="tmgo"><svg class="i"><use href="#i-download"/></svg>${t('Add them')}</button></div>`, el => {
    const upd = () => { const total = (S.items || []).length + +st.n, sheets = Math.ceil(total / 15);
      $('#tmsum', el).innerHTML = t('The set will have <b>{total}</b> thumbnails - {sheets} for Claude when it finds the patterns again.', {total: numStr(total), sheets: plural(sheets, 'sheet')}); };
    spSeg(el, '#tmn', st, 'n', upd); spSeg(el, '#tmo', st, 'order', upd); upd();
    $('#tmgo', el).onclick = async () => {
      $('#tmgo', el).disabled = true;
      try { await api('/api/jobs', {kind: 'thumbs_more', args: {set: S.name, n: +st.n, order: st.order}, queue: true});
        closeModal(); ping(); toast(tn(+st.n, 'Getting {n} more thumbnails', 'Getting {n} more thumbnails'), 'ok'); after(); }
      catch (e) { toast(e.message, 'err'); $('#tmgo', el).disabled = false; }
    };
  });
}
// ---- scripts & prompts (2026-10-18, the user: "it should also be able to analize propmpts ... make sure it is able
// to handle batches or multiple at the same time, imagine i wanted to analize 10 prompts at the same time i could and
// it wouldnt allucinate"): a text set = analysis\texts\<set> (motionlab\textsets.py) around texts that live in the
// prompt library. MotionLab numbers and measures them; Claude checks one at a time and a tool checks every quote
// against the text (prompts.verify_check) - how far it got is read from the set's files, never from Claude's words
const TX_MAX = 20;
const TX_KINDS = ['shot', 'image', 'hook', 'script', 'brief'];
// a kind's count in words (2026-10-19, Spanish: tn() per kind, the English as before: "2 video prompts", "1 hook")
const TX_WORD = {shot: n => tn(n, '{n} video prompt', '{n} video prompts'), image: n => tn(n, '{n} image prompt', '{n} image prompts'),
  hook: n => tn(n, '{n} hook', '{n} hooks'), script: n => tn(n, '{n} talking script', '{n} talking scripts'), brief: n => tn(n, '{n} brief', '{n} briefs')};
const txKinds = k => Object.entries(k || {}).sort((a, b) => b[1] - a[1]).map(([x, n]) => TX_WORD[x] ? TX_WORD[x](n) : `${n} ${x}${n === 1 ? '' : 's'}`).join(' · ');
// whose they are (the dialog's question): Prepare lists only the user's own scripts (the analysed creators' stay in
// their set and the prompt library)
const TX_WHO = {tested: t('Your own - your scripts also show in Prepare, every text in the prompt library.'),
  creator: t("Someone else's - kept on this PC, in this set and the prompt library (Prepare lists only yours)."),
  found: t("Where they came from is not known - like a creator's, Prepare leaves them out.")};
function textSetCard(s) {
  const when = strTime(s.updated), left = Math.max(0, s.count - s.checked);
  const badge = !s.count ? '' : !s.checked ? `<span class="pbadge todo" title="${ta('Claude has not checked them yet')}">${t('not checked by Claude')}</span>`
    : left ? `<span class="pbadge todo" title="${ta('the others wait for Claude')}">${t('Claude checked {n} of {total}', {n: s.checked, total: s.count})}</span>`
    : `<span class="pbadge" title="${ta('every text checked - every word Claude quotes was found in its text')}">${t('Claude checked all')}</span>`;
  return `<div class="card pcard txcard">${newTag(`tx:${s.name}@${Math.round(s.created || 0)}`, s.created)}<a class="clink" href="#/texts/${encodeURIComponent(s.name)}">
    <div class="ppic txpic">${s.first ? `<span class="txq">“${esc(s.first)}”</span>` : '<svg class="ic"><use href="#i-texts"/></svg>'}
      <span class="pbadges">${badge}</span>${when ? `<span class="pwhen">${esc(whenWords(when))}</span>` : ''}</div>
    <div class="cb"><span class="ct">${esc(s.label)}</span><div class="small">${txKinds(s.kinds) || plural(s.count, 'text')}${s.to_sort ? ` · <span class="amber">${t('{files} for Claude to read', {files: plural(s.to_sort, 'file')})}</span>` : ''}</div></div></a>
    <div class="pfacts"><span class="fchip sm">${t('Scripts & prompts')}</span>${s.has_patterns ? `<span class="small ok">${t('✓ patterns found')}</span>` : ''}</div>
    ${left || s.to_sort ? `<div class="cact"><span class="small fnl grow">${s.checked ? t('{n} of {total} checked by Claude', {n: s.checked, total: s.count}) : t('Next: Claude checks each one, part by part')}</span>${claudeBtn(s.prompt, s.checked ? t('Continue with Claude') : t('Check them with Claude'), 'review', `texts ${s.name}`, 'sm pri')}</div>` : ''}
    <span class="pdel">${delBtn('texts', s.name)}</span></div>`;
}
// Add scripts & prompts: paste them (a line of only --- between two) or drop files; MotionLab numbers them at once
// (POST /api/texts/split - nothing is saved yet) and the kind of each can be changed; then whose they are, and Claude's
// check now (one window for all) or later. pre = {set, label, count, who, creator, after} for the set page's Add more
async function addTextsModal(pre = {}) {
  const [ST, EST] = await Promise.all([api('/api/settings'), api('/api/estimate').catch(() => ({}))]);
  const cl = ST.tools.find(x => x.name === 'claude') || {};
  const room = pre.set ? Math.max(0, TX_MAX - (pre.count || 0)) : TX_MAX;
  const st = {who: pre.who || 'tested'}, files = [], kinds = {};
  let P = {items: [], unread: [], new: 0};
  modal(`<h2>${pre.set ? t('Add to {name}', {name: esc(pre.label || pre.set)}) : t('Analyze scripts & prompts')}</h2>
    <div class="small muted" style="margin-top:-4px">${pre.set ? t('Talking scripts, hooks, prompts for AI video and image tools, briefs - up to {n} more in this set.', {n: room}) : t('Talking scripts, hooks, prompts for AI video and image tools, briefs - up to {n} at a time.', {n: room})}
      ${t('MotionLab saves each one word for word and numbers it; Claude then checks them one at a time, part by part - and MotionLab makes sure every word it quotes is really in the text.')}</div>
    ${pre.set ? '' : `<div class="avstep"><b>1</b><span>${t('Name the set')}</span>${optTag(t('the first words when empty'))}</div>
      <input type="text" id="txname" placeholder="${ta('e.g. Seedance prompts I like')}" maxlength="60" style="max-width:360px">`}
    <div class="avstep"><b>${pre.set ? 1 : 2}</b><span>${t('The texts')}</span><span class="small muted">${t('several? a line with only --- between them')}</span></div>
    <textarea id="txpaste" rows="8" style="width:100%" spellcheck="false" placeholder="${ta('Paste a script or a prompt here…\n---\n…and the next one')}"></textarea>
    <label class="tsdrop" id="txdrop" style="margin-top:8px"><input type="file" id="txfiles" accept=".txt,.md,.docx,.pdf" multiple hidden>
      <span>${t('…or drop files here or <b>choose them</b> (.txt .md .docx .pdf) - a file is one text, unless it has lines of ---')}</span></label>
    <div class="txprev" id="txprev"></div>
    <div class="avstep"><b>${pre.set ? 2 : 3}</b><span>${t('Whose are they?')}</span></div>
    <div class="seg" id="txwho"><button data-v="tested">${t('Mine')}</button><button data-v="creator">${t("A creator's")}</button><button data-v="found">${t('Found somewhere')}</button></div>
    <input type="text" id="txcr" placeholder="${ta('their name and / or a link')}" value="${esc(pre.creator || '')}" style="width:100%;max-width:520px;margin-top:8px" hidden>
    <div class="small muted" id="txwhoh" style="margin-top:6px"></div>
    <div class="avstep"><b>${pre.set ? 3 : 4}</b><span>${t("Claude's check")}</span></div>
    <label class="chk avclaude"><input type="radio" name="txc" value="1" ${cl.found ? 'checked' : 'disabled'}><span>${t("<b>Claude checks them now</b> (recommended) - one Claude Code window, one text at a time: each part clear, vague or missing in the text's own words, then what they have in common.")}${cl.found ? '' : ` <span class="bad">${t('Claude Code was not found - Settings.')}</span>`}
      <span class="small muted" id="txest"></span></span></label>
    <label class="chk avclaude"><input type="radio" name="txc" value="0" ${cl.found ? '' : 'checked'}><span>${t("<b>Only save them</b> - check them later from the set's page.")}</span></label>
    <div class="row" style="margin-top:14px"><button class="btn pri big" id="txgo" disabled><svg class="i"><use href="#i-texts"/></svg>${t('Add them')}</button><span class="small muted" id="txsum"></span></div>`, el => {
    const paste = $('#txpaste', el), prev = $('#txprev', el);
    const source = () => {
      if (st.who !== 'creator') return {type: st.who};
      const w = $('#txcr', el).value.trim(), link = (w.match(/https?:\/\/\S+/) || [''])[0];
      return {type: 'creator', creator: w.replace(link, '').replace(/[\s,-]+$/, '').trim(), link};
    };
    const live = x => !x.dup && !x.in_set;
    const draw = () => {
      prev.innerHTML = P.items.map(x => `<div class="txrow${x.problem && live(x) ? ' bad' : live(x) ? '' : ' dup'}"><b class="txn">#${x.i}</b>
          <select data-sha="${esc(x.sha)}" title="${esc(x.kind_why || '')}"${x.known || !live(x) ? ' disabled' : ''}>${TX_KINDS.map(k => `<option value="${k}"${k === x.kind ? ' selected' : ''}>${esc(KSHORT[k])}</option>`).join('')}</select>
          <span class="grow txpv" title="${esc(x.preview)}">${esc(x.preview)}</span>
          <span class="small muted">${plural(x.words, 'word')}${x.from && x.from.file ? ` · ${esc(x.from.file)}` : ''}</span>
          ${x.dup ? `<span class="small amber">${t('the same as {n} - added once', {n: esc(x.dup)})}</span>` : x.in_set ? `<span class="small amber">${t('in the set already ({n})', {n: esc(x.in_set)})}</span>`
            : x.known ? `<span class="small ok" title="${ta('the same words are in your prompt library already - that one is used, not a copy')}">${t('in your library')}</span>` : ''}
          ${x.problem && live(x) ? `<span class="small bad">${esc(x.problem)}</span>` : ''}</div>`).join('')
        + (P.unread || []).map(u => `<div class="txrow"><b class="txn">·</b><span class="grow txpv" title="${ta(u.why || '')}">${esc(u.file)}</span><span class="small amber">${t('Claude reads it')}</span></div>`).join('');
      $$('select[data-sha]', prev).forEach(s => s.onchange = () => { kinds[s.dataset.sha] = s.value; refresh(); });
      const n = P.new || 0, bad = P.items.some(x => x.problem && live(x)), un = (P.unread || []).length;
      const known = P.items.filter(x => x.known && live(x)).length, b = $('#txgo', el);
      b.disabled = (!n && !un) || n > room || bad;
      b.innerHTML = `<svg class="i"><use href="#i-texts"/></svg>${n > 1 ? t('Add these {n}', {n}) : n === 1 ? t('Add it') : un ? tn(un, 'Add the file', 'Add the files') : t('Add them')}`;
      $('#txsum', el).innerHTML = n > room ? `<span class="bad">${pre.set ? t('at most {n} more in this set', {n: room}) : t('at most {n} at a time', {n: room})}</span>`
        : bad ? `<span class="bad">${t('a text marked red cannot be checked - fix it or take it out')}</span>`
        : n || un ? [n && tn(n, '{n} text numbered', '{n} texts numbered'), known && t('{n} from your library', {n: known}), un && t('{files} for Claude to read', {files: plural(un, 'file')})].filter(Boolean).join(' · ')
        : t('Paste a script or a prompt, or drop a file.');
      $('#txest', el).innerHTML = ' ' + estWords(EST.texts, n, 'text') + '.';
    };
    let seq = 0;
    const refresh = async () => {
      const my = ++seq, text = paste.value;
      if (!text.trim() && !files.length) { P = {items: [], unread: [], new: 0}; draw(); return; }
      try {
        const r = await api('/api/texts/split', {text, files: files.map(f => f.file), kinds, source: source(), set: pre.set || ''});
        if (my === seq) { P = r; draw(); }
      } catch (e) { if (my === seq) { prev.innerHTML = `<div class="small bad">${esc(e.message)}</div>`; $('#txgo', el).disabled = true; } }
    };
    paste.oninput = debounce(refresh, 350);
    const addF = async list => {
      for (const f of [...list]) {
        if (!/\.(txt|md|docx|pdf)$/i.test(f.name)) { toast(t('{name}: a .txt, .md, .docx or .pdf file', {name: f.name}), 'err'); continue; }
        if (f.size > 30e6) { toast(t('{name}: files up to 30 MB', {name: f.name}), 'err'); continue; }
        try { const r = await api('/api/prompts/file', {name: f.name, data: b64(await f.arrayBuffer())}); if (!files.some(x => x.file === r.file)) files.push(r); }
        catch (e) { toast(e.message, 'err'); }
      }
      refresh();
    };
    $('#txfiles', el).onchange = e => { addF(e.target.files); e.target.value = ''; };
    const dz = $('#txdrop', el);
    dz.ondragover = e => { e.preventDefault(); dz.classList.add('on'); };
    dz.ondragleave = () => dz.classList.remove('on');
    dz.ondrop = e => { e.preventDefault(); dz.classList.remove('on'); addF(e.dataTransfer.files); };
    const whoH = () => { $('#txcr', el).hidden = st.who !== 'creator'; $('#txwhoh', el).textContent = TX_WHO[st.who]; };
    spSeg(el, '#txwho', st, 'who', () => { whoH(); if (st.who === 'creator') $('#txcr', el).focus(); });
    whoH();
    $('#txgo', el).onclick = async () => {
      const b = $('#txgo', el), claude = ($('input[name=txc]:checked', el) || {}).value === '1';
      b.disabled = true;
      const body = {text: paste.value, files: files.map(f => f.file), kinds, source: source()};
      try {
        const r = pre.set ? await api(`/api/texts/${encodeURIComponent(pre.set)}/add`, body)
          : await api('/api/texts/new', {...body, label: $('#txname', el).value.trim()});
        closeModal();
        toast(tn(r.added + r.reused, '{n} text numbered in {set}', '{n} texts numbered in {set}', {set: r.label}) + (r.to_sort ? ' · ' + t('{files} for Claude to read', {files: plural(r.to_sort, 'file')}) : ''), 'ok');
        if (claude) openClaude(r.command, 'review', `texts ${r.set}`);
        if (pre.after) pre.after();
        else if (location.hash !== '#/analyze/texts') location.hash = '#/analyze/texts'; else route();
      } catch (e) { toast(e.message, 'err'); b.disabled = false; }
    };
    (pre.set ? paste : $('#txname', el)).focus();
    draw();
  }, 'wide');
}
// a text on its card: the first words - or, with a pattern lit, the part around the words it quotes, marked (spans =
// the tool's "at": the text's own characters, so the mark cannot drift)
function txExcerpt(text, spans) {
  const t = String(text || '');
  if (!spans || !spans.length) { const s = t.trim().replace(/\s+/g, ' '); return esc(s.length > 260 ? s.slice(0, 257) + '…' : s); }
  const sp = spans.slice().sort((x, y) => x[0] - y[0]);
  const a = Math.max(0, sp[0][0] - 80), b = Math.min(t.length, Math.max(sp[0][1] + 80, Math.min(sp[sp.length - 1][1] + 40, sp[0][0] + 520)));
  let out = a > 0 ? '…' : '', pos = a;
  for (const [s, e] of sp) { if (s < pos || e > b) continue; out += esc(t.slice(pos, s)) + `<mark class="tq">${esc(t.slice(s, e))}</mark>`; pos = e; }
  return out + esc(t.slice(pos, b)) + (b < t.length ? '…' : '');
}
function txCell(it) {
  const r = it.rec, f = it.facts || {};
  if (!r) return `<figure class="txcell gone" data-n="${it.n}"><div class="txct"><b>#${it.n}</b></div><div class="small muted">${t('Deleted from your prompt library.')}</div>
    <button class="btn sm ghost icon tsrm" data-n="${it.n}" title="${ta('Take #{n} out of the set', {n: it.n})}">✕</button></figure>`;
  const c = r.counts || {}, sc = f.script;
  const chk = it.checked ? `<span class="pill clear" title="${ta('parts Claude found clear')}">✓ ${c.clear || 0}</span><span class="pill vague" title="${ta('vague|parts')}">~ ${c.vague || 0}</span><span class="pill missing" title="${ta('missing|parts')}">✗ ${c.missing || 0}</span>${r.stars != null ? pstars(r.stars) : ''}`
    : it.stale ? `<span class="amber" title="${ta('its kind changed after Claude checked it')}">${t('checked as another kind')}</span>` : `<span class="amber">${t('not checked yet')}</span>`;
  const rate = r.rating ? `<span class="vr ${esc(r.rating)}" title="${ta('what it made - your rating')}">${r.rating === 'ok' ? t('OK') : r.rating === 'good' ? t('Good') : r.rating === 'bad' ? t('Bad') : esc(r.rating[0].toUpperCase() + r.rating.slice(1))}</span>` : '';
  return `<figure class="txcell" data-n="${it.n}" data-id="${esc(it.id)}" tabindex="0" title="${ta("Open it: the text, Claude's check part by part, your verdicts")}">
    <div class="txct"><b>#${it.n}</b><span class="kbadge k-${esc(it.kind)}" title="${esc(it.kind_why || '')}">${esc(KSHORT[it.kind] || it.kind)}</span>${r.source === 'creator' ? `<span class="small dim">${esc(r.creator || t("someone else's"))}</span>` : ''}</div>
    <b class="txtitle">${esc(r.title || f.title || '')}</b>
    <div class="txex">${txExcerpt(it.text)}</div>
    <div class="txcd"><span>${plural(f.words || 0, 'word')}${sc && sc.seconds ? ` · ≈ ${fmtSecs(sc.seconds)}` : ''}</span>${chk}${rate}</div>
    <button class="btn sm ghost icon tsrm" data-n="${it.n}" title="${ta('Take #{n} out of the set - it stays in your prompt library', {n: it.n})}">✕</button></figure>`;
}
const txSig = S => JSON.stringify([S.state.checked, S.state.left, S.state.patterns, (S.patterns || {}).date, (S.items || []).length, S.updated]);
// one set (#/texts/<set>), laid out like a thumbnail set: the texts in the main column - the lab's own numbers above
// them, folded ("MotionLab · no Claude") - and Claude's patterns in the review panel (reviewPanel, the one review
// pattern - 2026-10-19, as on a thumbnail set); a pattern lights up its texts and marks the words each example quotes;
// a card opens its prompt (Claude's check part by part). While Claude works on this set (the heartbeat's live line
// names it), the cards follow every 4 s
let TX_FOLD = false, TX_POLL = null;
async function pageTexts(main, name) {
  const S = await api('/api/texts/' + encodeURIComponent(name));
  const st = S.state, items = S.items || [], P = S.patterns, V = S.verdicts || {}, enc = encodeURIComponent(S.name), src = S.source || {};
  const pats = (P && P.patterns) || [];
  // a pattern's kind (textsets.PATTERN_KINDS) as the page says it; the kind itself stays the id
  const PKIND = {hook: t('hook|pattern kind'), structure: t('structure|pattern kind'), wording: t('wording|pattern kind'),
    camera: t('camera|pattern kind'), look: t('look|pattern kind'), length: t('length|pattern kind'), cta: t('cta|pattern kind'),
    voice: t('voice|pattern kind'), format: t('format|pattern kind'), other: t('other|pattern kind')};
  const byN = Object.fromEntries(items.map(it => [String(it.n), it])), label = `texts ${S.name}`;
  const go = !st.checked ? claudeBtn(st.prompt, t('Check them with Claude'), 'review', label, 'pri big')
    : st.left.length || st.to_sort.length || (st.items >= 3 && st.patterns !== 'ok')
      ? claudeBtn(st.prompt, t('Continue with Claude') + (st.left.length ? ' · ' + tn(st.left.length, '{n} left', '{n} left') : ''), 'review', label, 'pri big')
      : claudeBtn(st.prompt, t('Check them again'), 'review', label, 'big tsfind');
  const how = st.done ? `<span class="small ok">${t('✓ every text checked - every word Claude quotes was found in its text')}</span>`
    : st.to_sort.length ? `<span class="small amber">${t('{files} for Claude to read first: {names}', {files: plural(st.to_sort.length, 'file'), names: esc(st.to_sort.join(', '))})}</span>`
    : st.left.length && st.checked ? `<span class="small muted">${t('not checked yet: #{list}', {list: st.left.join(' #')})}</span>`
    : !st.left.length && st.items >= 3 && st.patterns !== 'ok' ? `<span class="small muted">${t('next: Claude names what they have in common')}</span>` : '';
  const claudeChip = `<span class="clchip" title="${ta('Claude names it; MotionLab finds every example it quotes in its text and counts them')}">Claude</span>`;
  const foldBtn = `<button class="btn sm ghost icon" id="txfold" title="${ta('Fold it away - the texts take the whole width')}">◂</button>`;
  // no patterns yet: the side says what Claude does there; with patterns it is the review panel (below)
  const side = P ? '' : `<div class="row sp tsside-h"><h2>${t('What they have in common')}</h2>${claudeChip}${foldBtn}</div>
    <div class="small muted">${st.items < 2 ? t('With 2 texts or more, Claude names what they have in common.')
      : t('Claude has not named what they have in common yet. Once each text is checked, it names what repeats - the hook, the structure, the wording, the camera, the look - and MotionLab finds every example it quotes in its text and counts them.')}</div>`;
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/analyze">${t('Analyser')}</a> / <a href="#/analyze/texts">${t('Scripts & prompts')}</a> / ${t('scripts & prompts')}</div><h1>${esc(S.label || S.name)}</h1>
      <div class="sub">${txKinds((S.summary || {}).kinds) || plural(st.items, 'text')} · ${t('Claude checked {n} of {total}', {n: st.checked, total: st.items})}${S.updated ? ` · ${esc(whenStr(S.updated))}` : ''}</div></div>
      <div class="row">${delBtn('texts', S.name, '#/analyze/texts', t('Delete'))}</div></div>
    <div class="toprow">${go}
      <button class="btn" id="txmore"${st.items >= TX_MAX ? ` disabled title="${ta('A set holds up to {n} texts', {n: TX_MAX})}"` : ''}><svg class="i"><use href="#i-texts"/></svg>${t('Add more')}</button>
      ${how}${st.disputed.length ? `<span class="small amber">${t('you marked parts of #{list} wrong or partly - Claude checks them again with your notes', {list: st.disputed.join(' #')})}</span>` : ''}
      <span class="grow"></span><button class="btn ghost" id="txopen"${TX_FOLD ? '' : ' hidden'}>${t('What they have in common')} ▸</button></div>
    <div class="tslayout${TX_FOLD ? ' folded' : ''}">
      <div class="tsmain">
        <details class="panel tsmeas"><summary><h2>${t('Measured by MotionLab')}</h2><span class="mlchip" title="${ta('counted from the words - Claude was not involved')}">${t('MotionLab · no Claude')}</span>
          <span class="small muted">${t('kinds, length, the words they share, twins - counted, not read')}</span></summary>
          <ul class="tslines">${(S.lines || []).map(l => `<li>${esc(l)}</li>`).join('')}</ul></details>
        <div class="txgrid">${items.map(txCell).join('')}</div>
      </div>
      <aside class="${P ? '' : 'panel '}tsside" id="txside">${side}</aside>
    </div>`;
  const redraw = async () => {                          // the same page again, where it was (not if the user went on)
    if (location.hash.split('?')[0] !== '#/texts/' + enc) return;
    if (rp) { await rp.flush(); rp.destroy(); }         // a note being typed is saved first
    const y = main.scrollTop; await pageTexts(main, S.name); main.scrollTop = y;
  };
  // a pattern (the panel's current row; a second click lets it go) lights up its texts and marks the words each of its
  // examples quotes
  const light = pid => {
    const p = pid ? pats.find(x => x.id === pid) : null, at = {};
    (p ? p.examples || [] : []).forEach(e => { (at[e.n] = at[e.n] || []).push(...(e.at || [])); });
    const on = new Set((p ? p.items || (p.examples || []).map(x => x.n) : []).map(String));
    $$('.txcell', main).forEach(c => {
      const hit = on.has(c.dataset.n), it = byN[c.dataset.n], ex = $('.txex', c);
      c.classList.toggle('hl', hit); c.classList.toggle('dimmed', !!p && !hit);
      if (ex && it) ex.innerHTML = txExcerpt(it.text, hit ? at[c.dataset.n] : null);
    });
    const first = p && $('.txcell.hl', main);
    if (first) first.scrollIntoView({block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  };
  const post = rvQueue();
  const rp = !P ? null : reviewPanel($('#txside', main), {
    title: t('What they have in common') + ' ' + claudeChip, head: foldBtn,
    top: P.summary ? `<details class="tssum"><summary class="small muted">${t('In short')} <span class="dim">· ${t('click to read')}</span></summary><p>${esc(P.summary)}</p></details>` : '',
    stale: st.patterns === 'stale' ? t('The set changed since Claude found these - Continue with Claude looks again.') : '',
    sections: [{id: 'patterns', ask: t('Is Claude right?'), intro: t('Click a pattern to light up its texts and the words it quotes, then say if it is really there.'), scale: 'claims', note: 'line',
      items: () => pats.map(p => { const ns = p.items || [...new Set((p.examples || []).map(x => x.n))];
        // how_many = the tool's "k of N" (textsets.py); said in the page's language when it is exactly that
        const hm = p.how_many || '', kof = p.k != null && p.of != null && hm === `${p.k} of ${p.of}`;
        return {id: p.id, label: `<span class="fchip sm">${esc(PKIND[p.kind] || p.kind || '')}</span> <b>${esc(p.what || '')}</b>`,
          sub: `<span title="${ta('counted by MotionLab from the examples it found in the texts')}">${kof ? t('{n} of {total}', {n: p.k, total: p.of}) : esc(hm)}</span>${ns.length ? ` · #${ns.map(esc).join(' #')}` : ''}`}; }),
      get: pid => V[pid] || {},
      set: (pid, a) => {                            // the set's verdicts.json (one home), the note too
        const note = a.note.trim();
        if (a.v || note) V[pid] = {v: a.v, note}; else delete V[pid];
        return post(() => api(`/api/texts/${enc}/verdicts`, {patterns: {[pid]: {v: a.v, note}}}));
      },
      empty: t('Claude named no pattern in this set.')}],
    start: false, deselect: true, onMove: (s, pid) => light(pid),
    send: {hint: t('Claude finishes what is left, then looks at the patterns again with your verdicts: it keeps the ones you marked correct, fixes the partly ones by your note and drops or redoes the wrong ones.'),
      cmd: st.prompt, task: 'review', name: label}});
  const lay = $('.tslayout', main);
  const fold = on => { TX_FOLD = on; lay.classList.toggle('folded', on); $('#txopen', main).hidden = !on; };
  $('#txfold', main).onclick = () => fold(true);
  $('#txopen', main).onclick = () => fold(false);
  $('#txmore', main).onclick = () => addTextsModal({set: S.name, label: S.label, count: st.items, after: redraw,
    who: src.type === 'creator' ? (src.creator || src.link ? 'creator' : 'found') : 'tested', creator: [src.creator, src.link].filter(Boolean).join(' ')});
  // a card = its prompt (the review area adds Previous / Next through ctx.ids and the quoted words lit from "at")
  const ctx = {set: S.name, ids: items.filter(it => it.rec).map(it => it.id), R: null,
    reload: async () => { ctx.R = await api('/api/prompts'); }, draw: () => redraw()};
  $$('.txcell[data-id]', main).forEach(c => {
    const open = async () => { try { if (!ctx.R) await ctx.reload(); promptModal(c.dataset.id, ctx); } catch (e) { toast(e.message, 'err'); } };
    c.onclick = e => { if (!e.target.closest('.tsrm')) open(); };
    c.onkeydown = e => { if (e.key === 'Enter' && e.target === c) open(); };
  });
  $$('.tsrm', main).forEach(b => b.onclick = async e => {
    e.stopPropagation();
    try { await api(`/api/texts/${enc}/remove`, {n: +b.dataset.n}); toast(t('#{n} is out of the set - it stays in your prompt library', {n: b.dataset.n}), 'ok'); redraw(); }
    catch (err) { toast(err.message, 'err'); }
  });
  if (TX_POLL) clearInterval(TX_POLL);
  let busy = LIVE.some(x => x.texts === S.name);
  const sig = txSig(S);
  TX_POLL = setInterval(async () => {
    const now = LIVE.some(x => x.texts === S.name);
    if (!now && !busy) return;
    busy = now;                                         // one more look after Claude's turn ends
    try { if (txSig(await api('/api/texts/' + enc)) !== sig) redraw(); } catch (e) { /* the next tick */ }
  }, 4000);
  onCleanup(() => { if (TX_POLL) { clearInterval(TX_POLL); TX_POLL = null; } });
}
function refCard(r) {
  const fl = r.flow, when = strTime(r.generated), P = r.pacing || {}, fmt = ((r.format || {}).label || '').split(' · ')[0];   // the shape only: the length is shown
  return `<div class="card pcard refcard ${fl.next ? 'n-' + fl.next : 'n-done'}">${newTag(`r:${r.name}@${Math.round(r.done_t || 0)}`, r.done_t)}<a class="clink" href="#/ref/${encodeURIComponent(r.name)}">
    <div class="ppic">${r.thumb ? `<img src="${fileUrl(r.thumb)}" loading="lazy" alt="">` : '<svg class="ic"><use href="#i-analyze"/></svg>'}
      <span class="pbadges">${fl.next === 'claude' ? `<span class="pbadge todo" title="${ta('Claude has not checked its effects yet')}">${t('not checked by Claude')}</span>` : ''}</span>
      ${when ? `<span class="pwhen" title="${ta('analysed {when}', {when: r.generated})}">${esc(whenWords(when))}</span>` : ''}</div>
    <div class="cb"><span class="ct"${r.label && r.label !== r.title ? ` title="${esc(r.title)}"` : ''}>${esc(r.label || r.title)}</span><div class="small">${[lenWords(r.frames, r.fps), r.category ? esc(t(r.category_label || '')) : '', fmt ? `<span class="muted">${esc(t(fmt))}</span>` : ''].filter(Boolean).join(' · ')}</div></div></a>
    <div class="pfacts"><span>${P.cuts_per_min != null ? t('<b>{n}</b> cuts/min', {n: numStr(P.cuts_per_min)}) + ' · ' : ''}${tn(r.events, '<b>{n}</b> effect', '<b>{n}</b> effects')}</span>${focusChip(r.focus)}</div>
    <div class="cact"><span class="small fnl grow ${fl.next ? '' : 'ok'}">${esc(flowNext(fl))}</span>${flowAction(r, fl)}</div>
    <span class="pdel">${delBtn('reference', r.name)}</span></div>`;
}
