/* MotionLab app - js/agency.js: Content agency (#/agency): calendar, your videos, tests, what works, monthly review.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ content agency
// 0.6.0 (docs\plans.md steps 12-19; the user, 2026-10-25: "own row named 'Content agency'", "i kinda want the content
// calendar first"): the plan around the videos. Step 12 = the content calendar - knowledge\local\calendar.json through
// GET / POST /api/agency (motionlab\agency.py checks every save): a month of posts as chips (status colour, platforms,
// time), dragged from day to day or to the Ideas column (a post without a date); the weekly rhythm (the days the user
// aims to post) as dashed slots + "this week n of m"; a post's pop-up (title, date, time, platforms, status, the
// MotionLab video, the sound to add in the app, notes, the links once posted); *Add to Windows Calendar* = the .ics
const AG_STATUS = [['idea', t('Idea'), '--dim'], ['scripted', t('Scripted'), '--violet'], ['filmed', t('Filmed'), '--cyan'],
                   ['edited', t('Edited'), '--amber'], ['ready', t('Ready'), '--green'], ['posted', t('Posted'), '--agency']];
const AG_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
const agIso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const agDay = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const agWeekday = i => new Intl.DateTimeFormat(LANG, {weekday: 'short'}).format(new Date(2026, 9, 26 + i)).replace(/\.$/, '');  // 2026-10-26 = a Monday
const AG_TABS = [['calendar', t('Calendar'), 'i-calendar'], ['videos', t('Your videos'), 'i-film'], ['tests', t('Tests'), 'i-ab'],
  ['learn', t('What works'), 'i-target'], ['month', t('Monthly review'), 'i-month']];
const agNum = n => n == null ? '–' : new Intl.NumberFormat(LANG, {notation: 'compact', maximumFractionDigits: 1}).format(n);
// 0.6.0 step 15: before you post, per platform ([key, words]; "all" on every platform) - ticked on the post
const AG_CHECKS = () => ({all: [['package', t('Title and description written')], ['cover', t('Cover or thumbnail picked')],
    ['captions', t('Captions on')], ['link', t('Link or pinned comment')], ['ad', t('If it is an ad: the paid-partnership label')]],
  youtube: [['chapters', t('Chapters in the description')], ['abtest', t('Thumbnails in Test & compare')], ['endscreen', t('End screen and cards')]],
  tiktok: [['sound', t('The sound added in the app')], ['hashtags', t('3 to 5 hashtags')], ['pin', t('A comment pinned')]],
  instagram: [['sound', t('The sound added in the app')], ['hashtags', t('Hashtags')], ['grid', t('Cover cropped for the grid')], ['story', t('Shared to your story')]],
  x: [['hook', t('The first line hooks')]], linkedin: [['hook', t('The first line hooks')]], threads: [['hook', t('The first line hooks')]],
  facebook: [['sound', t('The sound added in the app')]]});
// the shape each platform plays best (the repurpose line: what the video is vs what each platform wants)
const AG_SHAPE = {youtube: ['16:9', t('16:9 - or 9:16 as a Short')], tiktok: ['9:16', '9:16'], instagram: ['9:16', t('9:16 - 4:5 in the feed')],
  facebook: ['9:16', t('9:16 or 1:1')], x: ['16:9', t('16:9 or 1:1')], linkedin: ['1:1', t('1:1 or 16:9')], threads: ['9:16', t('9:16 or 1:1')], twitch: ['16:9', '16:9']};
// 0.6.0 step 16: where each platform shows your own audience's hours, and a generic time when you have not typed yours
const AG_WHEN_WHERE = () => ({youtube: t('YouTube Studio > Analytics > Audience > When your viewers are on YouTube'),
  instagram: t('Instagram > Professional dashboard > Total followers > Most active times'), tiktok: t('TikTok Studio > Analytics > Followers > Follower activity'),
  facebook: t('Meta Business Suite > Insights > Audience')});
const AG_GENERIC = () => ({youtube: t('The hour matters little to YouTube - post when you can answer comments in the first hour.'),
  tiktok: t('Generic: weekday evenings, 18:00 to 21:00 - the studies disagree.'), instagram: t('Generic: weekday lunchtime or evening - the studies disagree.')});
const agWhenLabel = b => { const [d, tm] = String(b).split(' '); const i = AG_DAYS.indexOf(d); return `${i < 0 ? t('any day') : agWeekday(i)} ${tm || ''}`; };
// a post's video on a platform (its link) -> the views your page checks saw near 48 h, 7 days and 28 days after it went
// up (a check between half and twice that age counts; else -), its views now and the stats file's numbers (step 12)
const agVidId = (plat, url) => { const u = String(url || ''); let m;
  if (plat === 'youtube' && (m = u.match(/(?:v=|youtu\.be\/|shorts\/)([\w-]{11})/))) return m[1];
  if (plat === 'tiktok' && (m = u.match(/video\/(\d{8,})/))) return m[1];
  if ((m = u.match(/\/(?:reel|reels|p)\/([\w-]+)/))) return m[1];
  return null; };
function agHowItDid(plat, url, SOC, pageVids) {
  const id = agVidId(plat, url);
  if (!id) return '';
  const v = pageVids.find(x => x.platform === plat && String(x.id) === id);
  const S = (((SOC.stats || {}).videos || {})[plat]) || {};
  const nu = u => String(u || '').replace(/[?#].*$/, '').replace(/\/+$/, '').toLowerCase();
  const imp = S[id] || Object.values(S).find(r => (r.url && nu(r.url) === nu(url)) || String(r.id || '') === id);
  if (!v && !imp) return '';
  const h = (SOC.history || {})[`${plat}:${id}`] || [], t0 = v && v.date ? Date.parse(`${v.date}T${v.time || '12:00'}`) / 1000 : null;
  const near = hrs => { if (!t0) return null; let best = null;
    for (const [ts, n] of h) { const age = (ts - t0) / 3600; if (age >= hrs * 0.5 && age <= hrs * 2 && (!best || Math.abs(ts - t0 - hrs * 3600) < Math.abs(best[0] - t0 - hrs * 3600))) best = [ts, n]; }
    return best; };
  const cells = [['48 h', 48], [t('7 days'), 168], [t('28 days'), 672]].map(([l, hrs]) => { const b = near(hrs);
    return `<span title="${b ? ta('checked {when}', {when: whenStr(new Date(b[0] * 1000).toISOString().slice(0, 16).replace('T', ' '))}) : ta('no check near that age')}">${l}: <b>${b ? agNum(b[1]) : '–'}</b></span>`; });
  const now = v && v.views != null ? v.views : imp && imp.views;
  const R = (SOC.retention || {})[`${plat}:${id}`];           // where people left (2026-11-02): your traced graph
  return `<div class="agdid1">${brandPgLogo(plat)}<span>${t('now')}: <b>${agNum(now)}</b> ${t('views')}</span>${cells.join('')}${agImpLine(imp)}${R
    ? `<span class="agimp" title="${ta('From your retention graph (Your videos > Where people left)')}">${t('{pct} still watching at 3 s', {pct: rtPct((R.summary || {}).hold_3s)})}</span>` : ''}</div>`;
}
const agImpLine = r => !r ? '' : `<span class="agimp" title="${ta('From the stats file you imported ({file})', {file: r.file || ''})}">${[
  r.watch_h != null ? t('{n} h watched', {n: numLoc(Math.round(r.watch_h * 10) / 10)}) : '',
  r.avg_pct != null ? t('{n} % viewed', {n: numLoc(Math.round(r.avg_pct))}) : r.avg_view_s != null ? t('{n} s average view', {n: Math.round(r.avg_view_s)}) : '',
  r.ctr != null ? `CTR ${numLoc(r.ctr)} %` : '', r.shares != null ? `↗ ${agNum(r.shares)}` : ''].filter(Boolean).join(' · ')}</span>`;
// Check my pages (agency_check) followed from any page, like the website import: the bar + the stage on Your videos,
// a toast when it ends elsewhere; the page redraws with what it found
const AG_STAGE = {youtube: t('Reading YouTube'), tiktok: t('Reading TikTok'), details: t('Reading the newest videos'), done: t('Almost done')};
let AG_CHECK = null;
function agCheckPaint() {
  const b = $('#agchk'), bar = $('#agprog'), st = $('#agchkst');
  if (!b) return;
  const on = !!AG_CHECK;
  b.disabled = on; b.classList.toggle('busy', on); bar.hidden = !on;
  if (on) { $('i', bar).style.width = Math.max(3, AG_CHECK.pct) + '%'; st.textContent = `${AG_STAGE[AG_CHECK.stage] || t('Reading your pages…')} · ${Math.round(AG_CHECK.pct)} %`; }
  else st.textContent = st.dataset.idle || '';
}
async function agCheckWatch(id) {
  if (AG_CHECK && AG_CHECK.id === id) return;
  AG_CHECK = {id, pct: 2, stage: ''}; agCheckPaint();
  let since = 0, last = '';
  for (;;) {
    await new Promise(r => setTimeout(r, 900));
    let s; try { s = await api(`/api/jobs/${id}?since=${since}`); } catch (e) { continue; }
    const lines = (s.log || []).map(l => String(l).trim()).filter(Boolean);
    since += (s.log || []).length;
    const pr = lines.map(l => /^progress (\d+(?:\.\d+)?) (\w+)/.exec(l)).filter(Boolean).pop();
    if (pr) Object.assign(AG_CHECK, {pct: +pr[1], stage: pr[2]});
    last = lines.filter(l => !l.startsWith('progress ')).pop() || last;
    if (['running', 'queued', 'cancelling'].includes(s.status)) { agCheckPaint(); continue; }
    AG_CHECK = null; agCheckPaint();
    if (s.status !== 'done') { toast(t('Could not read your pages: {why}', {why: (last || s.status).replace(/^ERROR: /, '')}), 'err'); return; }
    if (/^#\/agency/.test(location.hash)) route(); else toast(t('Your pages are read - open Content agency to see your videos'), 'ok');
    return;
  }
}
// ---- Where people left (2026-11-02, docs\plans.md *Learn from your own posts* R1; motionlab\retention.py): your own
// video's retention graph from a screenshot - you put four lines on its axes, MotionLab follows the curve itself (no
// Claude, no login): the share still watching every second (unknown where it cannot see the curve), the holds at 3 s,
// 10 s and the end, the steepest 3-second drops. SPARK lines them up with the words (pageSpark)
const RT_WHERE = () => [['tiktok', t("TikTok Studio: the video's analytics - its retention graph")],
  ['youtube', t("YouTube Studio: the video's Analytics - Audience retention")],
  ['instagram', t("Instagram: the reel's insights - Retention")]];
const rtPct = v => v == null ? '–' : `${numLoc(Math.round(v))} %`;
// a curve as SVG (points [[s, % | null]] - a gap stays a gap); o: {w, h, mini, drops: [{s}], play (a playhead line)}
function retSvg(points, endS, o = {}) {
  const w = o.w || 600, h = o.h || 150, pad = o.mini ? 2 : 4, end = Math.max(1, +endS || 1);
  const max = Math.max(100, ...points.map(p => p[1] || 0));
  const X = s => pad + (w - 2 * pad) * s / end, Y = p => pad + (h - 2 * pad) * (1 - p / max);
  const segs = []; let cur = [];
  points.forEach(([s, p]) => { if (p == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push(`${X(s).toFixed(1)},${Y(p).toFixed(1)}`); });
  if (cur.length) segs.push(cur);
  const bands = (o.drops || []).map((d, i) => `<rect class="rtband${i ? '' : ' first'}" x="${X(d.s).toFixed(1)}" y="0" width="${(X(d.s + 3) - X(d.s)).toFixed(1)}" height="${h}"/>`).join('');
  const grid = o.mini ? '' : [0, 50, 100].map(p => `<line class="rtgrid" x1="${pad}" x2="${w - pad}" y1="${Y(p).toFixed(1)}" y2="${Y(p).toFixed(1)}"/><text class="rtax" x="${pad + 2}" y="${(Y(p) - 3).toFixed(1)}">${p} %</text>`).join('');
  return `<svg class="rtsvg${o.mini ? ' mini' : ''}" viewBox="0 0 ${w} ${h}"${o.mini ? ' preserveAspectRatio="none"' : ''} data-end="${end}" data-pad="${pad}" data-w="${w}">${grid}${bands}
    ${segs.map(sg => sg.length === 1 ? `<circle cx="${sg[0].split(',')[0]}" cy="${sg[0].split(',')[1]}" r="1.5"/>` : `<polyline points="${sg.join(' ')}"/>`).join('')}${o.play ? `<line class="rtplay" x1="${pad}" x2="${pad}" y1="0" y2="${h}"/>` : ''}</svg>`;
}
// the dialog: post = {key, url, title, duration, platform, entry (what was saved: image, axes, colour)}; done(entry | null)
function retentionModal(post, done) {
  const E = post.entry && post.entry.image ? post.entry : null;
  let S = E ? {image: E.image, axes: {...E.axes}, colour: E.colour || null} : null, seq = 0;
  modal(`<h2><svg class="i"><use href="#i-retention"/></svg> ${t('Where people left')}</h2>
    <div class="small muted rtsub">${post.platform ? brandPgLogo(post.platform) : ''}<span>${esc(post.title || '')}</span></div><div id="rtbody"></div>`, el => {
    const body = $('#rtbody', el);
    const pick = () => {
      body.innerHTML = `<div class="rtwhere">${RT_WHERE().map(([p, l]) => `<div${p === post.platform ? ' class="on"' : ''}>${brandPgLogo(p)}<span>${esc(l)}</span></div>`).join('')}</div>
        <div class="small muted">${t('Take the screenshot with the mouse away from the graph - the whole graph, with its axis labels.')}</div>
        <label class="rtdrop" id="rtdrop"><svg class="i"><use href="#i-upload"/></svg><b>${t('Paste the screenshot here (Ctrl+V)')}</b>
          <span class="small muted">${t('or drop it here, or click to pick the file')}</span><input type="file" accept="image/png,image/jpeg,image/webp" hidden></label>
        <div class="small muted">${t('Your screenshot stays on this PC. MotionLab reads the curve itself - no login, nothing sent anywhere.')}</div>`;
      const drop = $('#rtdrop', body);
      const send = async f => {
        if (!f || !/^image\//.test(f.type || '')) { toast(t('That is not a picture - a .png, .jpg or .webp screenshot'), 'err'); return; }
        drop.classList.add('busy');
        try {
          const r = await fetch(`/api/agency/retention/upload?name=${encodeURIComponent(f.name || 'graph.png')}`,
            {method: 'POST', headers: {'X-ML-Token': TOKEN, 'Content-Type': 'application/octet-stream'}, body: f});
          const j = await r.json().catch(() => ({}));
          if (!r.ok) throw new Error(j.error || r.status);
          const g = j.guess;
          S = {image: j.image, axes: {x0: g.x0, x1: g.x1, y_top: g.y_top, y_bot: g.y_bot, top: 100, bottom: 0, end_s: post.duration || 30}, colour: null};
          edit();
        } catch (e) { toast(e.message, 'err'); drop.classList.remove('busy'); }
      };
      $('input', drop).onchange = e => send(e.target.files[0]);
      drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
      drop.ondragleave = () => drop.classList.remove('over');
      drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over'); send(e.dataTransfer.files[0]); };
      const onPaste = e => {                       // gone with the dialog: the listener removes itself
        if (!document.body.contains(drop)) { document.removeEventListener('paste', onPaste); return; }
        const it = [...((e.clipboardData || {}).items || [])].find(x => x.type.startsWith('image/'));
        if (it) { e.preventDefault(); send(it.getAsFile()); }
      };
      document.addEventListener('paste', onPaste);
    };
    const edit = () => {
      body.innerHTML = `<div class="rtedit"><div class="rtpic" id="rtpic"><img id="rtimg" src="${fileUrl(S.image)}" alt="" draggable="false"><svg id="rtdots" class="rtdots"></svg>
          ${['x0', 'x1', 'y_top', 'y_bot'].map(k => `<div class="rtln ${k[0] === 'x' ? 'v' : 'h'}" data-k="${k}"><span></span></div>`).join('')}</div>
        <div class="rtside">
          <div class="small muted">${t('Drag the four lines onto the graph: the two upright ones on its first and last second, the two flat ones on gridlines whose % you type below. The dots show what MotionLab reads - click the curve if they miss it.')}</div>
          <div class="rtvals"><label>${t('Top line')}<span><input type="number" id="rttop" step="1" value="${S.axes.top}"> %</span></label>
            <label>${t('Bottom line')}<span><input type="number" id="rtbot" step="1" value="${S.axes.bottom}"> %</span></label>
            <label>${t('The end')}<span><input type="number" id="rtend" step="0.1" min="1" value="${S.axes.end_s}"> s</span></label></div>
          <div class="rtcol"><span>${t('The curve')}</span><i id="rtsw"></i><span class="small muted" id="rtcolw"></span><button class="btn sm ghost" id="rtauto" hidden>${t('Find it again')}</button></div>
          <div class="rtnums" id="rtnums"><span class="small muted">${t('Reading the curve…')}</span></div>
          <div class="row"><button class="btn pri" id="rtok">${t('Save')}</button><button class="btn ghost" id="rtnew">${t('Another screenshot')}</button>
            <span class="grow"></span>${E ? `<button class="btn danger" id="rtdel">${t('Forget this curve')}</button>` : ''}</div></div></div>`;
      const img = $('#rtimg', body), pic = $('#rtpic', body), dots = $('#rtdots', body);
      let W = 1, H = 1;
      const sc = () => img.clientWidth / W;
      const place = () => {
        $$('.rtln', pic).forEach(l => { const k = l.dataset.k, v = S.axes[k] * sc();
          if (k[0] === 'x') l.style.left = v + 'px'; else l.style.top = v + 'px';
          $('span', l).textContent = k === 'x0' ? t('0 s') : k === 'x1' ? t('the end · {n} s', {n: numLoc(S.axes.end_s)}) : `${numLoc(k === 'y_top' ? S.axes.top : S.axes.bottom)} %`; });
      };
      const nums = r => { const M = r.summary;
        $('#rtnums', body).innerHTML = `<div class="rtnrow"><span><b>${rtPct(M.hold_3s)}</b>${t('still watching at 3 s')}</span><span><b>${rtPct(M.hold_10s)}</b>${t('at 10 s')}</span><span><b>${rtPct(M.end)}</b>${t('at the end')}</span></div>
          ${M.drops.length ? `<div class="small">${t('The steepest drop: {n} % of those still watching left within 3 seconds - red on the graph.', {n: numLoc(Math.round(M.drops[0].loss))})}</div>` : ''}
          <div class="small ${r.found < 0.9 ? 'amber' : 'muted'}">${t('{seen} of {total} seconds read', {seen: M.seen, total: M.total})}${M.gaps.length ? ' - ' + t('the rest stays unknown, never guessed') : ''}</div>`;
        $('#rtsw', body).style.background = `rgb(${r.colour.join(',')})`;
        $('#rtcolw', body).textContent = S.colour ? t('picked by you') : t('found by MotionLab');
        $('#rtauto', body).hidden = !S.colour;
        const A = r.axes, px = s => A.x0 + (A.x1 - A.x0) * s / A.end_s, py = p => A.y_bot - (p - A.bottom) / (A.top - A.bottom) * (A.y_bot - A.y_top);
        const d0 = M.drops[0], rad = Math.max(2, W / 260);
        dots.innerHTML = (d0 ? `<rect class="rtband first" x="${px(d0.s)}" y="${A.y_top}" width="${px(d0.s + 3) - px(d0.s)}" height="${A.y_bot - A.y_top}"/>` : '')
          + r.points.filter(p => p[1] != null).map(([s, p]) => `<circle cx="${px(s).toFixed(1)}" cy="${py(p).toFixed(1)}" r="${rad}"/>`).join('');
      };
      const trace = debounce(async () => {
        const my = ++seq;
        try { const r = await api('/api/agency/retention/trace', {image: S.image, axes: S.axes, colour: S.colour}); if (my === seq) nums(r); }
        catch (e) { if (my !== seq) return; dots.innerHTML = ''; $('#rtnums', body).innerHTML = `<div class="small bad">${esc(e.message)}</div>`; }
      }, 220);
      const ready = () => { W = img.naturalWidth || 1; H = img.naturalHeight || 1; dots.setAttribute('viewBox', `0 0 ${W} ${H}`); place(); trace(); };
      if (img.complete && img.naturalWidth) ready(); else img.onload = ready;
      const onResize = () => { if (!document.body.contains(img)) { removeEventListener('resize', onResize); return; } place(); };
      addEventListener('resize', onResize);
      $$('.rtln', pic).forEach(l => l.onpointerdown = e => {
        e.preventDefault(); l.setPointerCapture(e.pointerId); l.classList.add('drag');
        const k = l.dataset.k;
        l.onpointermove = ev => { const r = img.getBoundingClientRect();
          S.axes[k] = Math.round(k[0] === 'x' ? clamp((ev.clientX - r.left) / sc(), 0, W - 1) : clamp((ev.clientY - r.top) / sc(), 0, H - 1)); place(); };
        l.onpointerup = () => { l.onpointermove = null; l.classList.remove('drag'); trace(); };
      });
      img.onclick = e => {                              // a click on the curve = its colour (the most saturated pixel near it)
        const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
        const cx = cv.getContext('2d', {willReadFrequently: true}); cx.drawImage(img, 0, 0);
        const r = img.getBoundingClientRect(), x = Math.round((e.clientX - r.left) / sc()), y = Math.round((e.clientY - r.top) / sc());
        const D = cx.getImageData(clamp(x - 3, 0, W - 7), clamp(y - 3, 0, H - 7), 7, 7).data;
        let best = null, bs = -1;
        for (let i = 0; i < D.length; i += 4) { const mx = Math.max(D[i], D[i + 1], D[i + 2]), mn = Math.min(D[i], D[i + 1], D[i + 2]), s = mx ? (mx - mn) / mx : 0;
          if (s > bs) { bs = s; best = [D[i], D[i + 1], D[i + 2]]; } }
        if (best) { S.colour = best; trace(); }
      };
      $('#rtauto', body).onclick = () => { S.colour = null; trace(); };
      [['#rttop', 'top'], ['#rtbot', 'bottom'], ['#rtend', 'end_s']].forEach(([id, k]) => $(id, body).oninput = e => { const v = parseFloat(e.target.value);
        if (Number.isFinite(v)) { S.axes[k] = v; place(); trace(); } });
      $('#rtnew', body).onclick = () => { S = null; pick(); };
      $('#rtok', body).onclick = async () => {
        try {
          const r = await api('/api/agency/retention', {key: post.key, url: post.url || '', title: post.title || '', image: S.image, axes: S.axes, colour: S.colour});
          closeModal(); toast(t('Saved - where people left is on the video now'), 'ok'); if (done) done(r);
        } catch (e) { toast(e.message, 'err'); }
      };
      if (E) $('#rtdel', body).onclick = async () => {
        try { await api('/api/agency/retention', {key: post.key, remove: true}); closeModal(); toast(t('The curve is forgotten - your screenshot stays on this PC'), 'ok'); if (done) done(null); }
        catch (e) { toast(e.message, 'err'); }
      };
    };
    S ? edit() : pick();
  }, 'wide rtmodal');
}
// ---- Tests of one idea (2026-11-02, plans.md *Learn from your own posts* R2; motionlab\experiments.py): two or three
// versions on the same platform, decided by one number picked first; Claude's keep / change / cut for the next one
const EX_STATE = () => ({planned: [t('Not posted yet'), '--dim'], testing: [t('Waiting for numbers'), '--amber'],
  compared: [t('Results in'), '--agency'], reviewed: [t('Reviewed by Claude'), '--violet'], closed: [t('Closed'), '--green']});
const EX_METRIC = () => ({views_48h: t('views at 48 h'), views_7d: t('views at 7 days'), views_28d: t('views at 28 days'),
  hold_3s: t('still watching at 3 s'), hold_10s: t('still watching at 10 s'), end: t('still watching at the end'),
  likes_per_1k: t('likes per 1,000 views'), comments_per_1k: t('comments per 1,000 views'), avg_pct: t('average % viewed')});
const EX_WHY = () => ({not_posted: t('not posted yet'), no_check: t('no check near that age yet - press Check my pages then'),
  not_checked: t('not on your pages yet - press Check my pages'), not_read: t('Instagram is not read here - decide by a retention graph or your stats file'),
  no_graph: t('no retention graph yet - add it in Your videos'), not_seen: t('that second could not be read on its graph'),
  no_stats: t('not in a stats file you imported'), few_views: t('fewer views than the minimum'), unknown: t('not known yet')});
const EX_KIND = () => ({keep: t('Keep'), change: t('Change'), cut: t('Cut|remove')});
const EX_HOW = () => ({edit_only: t('edit only'), re_record: t('re-record')});
const EX_PCT = ['hold_3s', 'hold_10s', 'end', 'avg_pct'];
const EXC = {A: 'var(--agency)', B: 'var(--amber)', C: 'var(--pink)'};
const exVal = (k, v) => v == null ? '–' : EX_PCT.includes(k) ? rtPct(v) : k.endsWith('_per_1k') ? numLoc(v) : agNum(v);
const exResLine = T => { const R = T.result || {}, W = (R.waiting || [])[0];
  return R.state === 'winner' ? `<span class="exres win" style="--vc: ${EXC[R.winner]}">${t('{v} is ahead by your rule', {v: R.winner})}</span>`
    : R.state === 'too_close' ? `<span class="exres close">${t('Too close to call')}</span>`
    : `<span class="exres wait">${W ? `${esc(W.version)}: ${esc(EX_WHY()[W.why] || W.why)}` : t('Waiting for numbers')}</span>`; };
// ---- What works (2026-11-02, plans.md *Learn from your own posts* R3; motionlab\findings.py): patterns across your own
// posts, measured features only; a hunch until new posts confirm it (likely, settled), weakened / refuted / stale
const FD_ST = () => ({hunch: [t('Hunch'), '--amber'], likely: [t('Likely'), '--agency'], settled: [t('Settled'), '--green'],
  stale: [t('Stale'), '--dim'], refuted: [t('Refuted'), '--red']});
const FD_FEAT = () => ({length_s: t('length'), posted_hour: t('the hour it went up'), weekday: t('the day it went up'),
  pillar: t('the content pillar'), hook_text: t('text on screen in the first 3 s'), hook_cuts: t('cuts in the first 3 s'),
  hook_words: t('words in the first 3 s'), first_cut_s: t('the first cut'), cuts_per_min: t('cuts per minute'), words_per_min: t('words per minute')});
const FD_UNIT = {length_s: 's', first_cut_s: 's'};
const fdSide = ft => ft.key === 'weekday' ? t('posted on {day}', {day: agWeekday(AG_DAYS.indexOf(ft.value))})
  : ft.key === 'pillar' ? t('in the pillar “{p}”', {p: esc(ft.value)})
  : ft.key === 'posted_hour' ? t('posted by {h}:59', {h: pad(ft.value)})
  : ft.op === 'yes' ? t('with {what}', {what: FD_FEAT()[ft.key]}) : ft.op === 'no' ? t('without {what}', {what: FD_FEAT()[ft.key]})
  : ft.key === 'length_s' ? t('up to {v} long', {v: numLoc(ft.value) + ' s'})
  : t('with {what} up to {v}', {what: FD_FEAT()[ft.key], v: numLoc(ft.value) + (FD_UNIT[ft.key] ? ' ' + FD_UNIT[ft.key] : '')});
const fdClaim = f => { const v = {platform: esc(BRAND_PAGES[f.platform] || f.platform), side: fdSide(f.feature), metric: `<b>${esc(EX_METRIC()[f.metric] || f.metric)}</b>`};
  return f.direction === 'higher' ? t('{platform} videos {side}: {metric} is higher than for the rest', v) : t('{platform} videos {side}: {metric} is lower than for the rest', v); };
const fdRun = r => r.verdict === 'supports' ? t('agreed') : r.verdict === 'contradicts' ? t('went the other way')
  : r.why === 'few' ? t('too few videos to tell') : r.why === 'one_video' ? t("one video carried it - can't tell") : t('too close to tell');
const fdNums = (m, r) => r && r.med_yes != null ? `<div class="fdnums"><b>${exVal(m, r.med_yes)}</b> ${t('against {v} for the rest', {v: exVal(m, r.med_no)})} · ${t('{a} / {b} videos', {a: r.n_yes, b: r.n_no})}</div>` : '';
const fdRows = (rows, m) => rows.length ? `<div class="fdrows">${rows.slice(0, 12).map(p => `<a class="fdrow" href="${esc(p.url || '#')}" target="_blank" rel="noopener">
    ${p.thumb ? `<img src="${fileUrl(p.thumb)}" loading="lazy" alt="">` : '<i></i>'}<span>${esc(p.title || p.key)}</span><b>${exVal(m, p.value)}</b></a>`).join('')}
    ${rows.length > 12 ? `<div class="small dim">${t('+{n} more', {n: rows.length - 12})}</div>` : ''}</div>` : '<div class="small dim">–</div>';
function fdCard(f) {
  const [sl, sc] = FD_ST()[f.status] || ['', '--dim'], last = f.runs[f.runs.length - 1] || {};
  const shown = [...f.runs].reverse().find(r => r.med_yes != null);
  return `<div class="fdcard st-${f.status}"><div class="fdh"><span class="exst" style="--sc: var(${sc})">${sl}</span>
      ${f.status !== 'refuted' ? `<span class="fddots" title="${ta('{n} of 3 confirmations by separate posts', {n: Math.min(3, f.confirmations)})}">${[1, 2, 3].map(i => `<i class="${i <= f.confirmations ? 'on' : ''}"></i>`).join('')}</span>` : ''}
      ${f.weakened && f.status !== 'refuted' ? `<span class="extt" title="${ta('New posts could not tell - one step down')}">${t('weakened')}</span>` : ''}${f.decayed ? `<span class="extt">${t('untested {n} days', {n: f.days})}</span>` : ''}
      <span class="grow"></span><span class="small dim">${t('tested {when}', {when: esc(whenStr(f.last_tested) || f.last_tested)})}</span></div>
    <p class="fdclaim">${fdClaim(f)}</p>${fdNums(f.metric, shown)}
    ${last.verdict && last !== shown ? `<div class="small muted">${t('Last test: {what}', {what: fdRun(last)})}</div>` : ''}
    ${f.status === 'refuted' ? (r => `<div class="small bad">${r ? t('Refuted {when} - new posts went the other way: {a} against {b} for the rest ({n} / {m} videos)',
      {when: esc(whenStr(r.date) || r.date), a: exVal(f.metric, r.med_yes), b: exVal(f.metric, r.med_no), n: r.n_yes, m: r.n_no}) : t('Refuted - new posts went the other way')}</div>`)(
      [...f.runs].reverse().find(r => r.verdict === 'contradicts')) : ''}
    <details class="fold"><summary>${t('The videos on each side, and every test')}</summary><div class="in">
      <div class="fdsides"><div><h4>${t('This pattern')}</h4>${fdRows(f.yes, f.metric)}</div><div><h4>${t('The rest')}</h4>${fdRows(f.no, f.metric)}</div></div>
      <table class="sptab">${f.runs.map(r => `<tr><td class="dim">${esc(whenStr(r.date) || r.date)}</td><td>${fdRun(r)}</td><td class="dim">${tn(r.new || 0, '{n} new video', '{n} new videos')}</td><td>${r.counted ? '✓' : ''}</td></tr>`).join('')}</table></div></details>
    <div class="row"><span class="grow"></span><button class="btn sm ghost" data-fdx="${esc(f.id)}">${t('Forget')}</button></div></div>`;
}
// ---- Monthly review (2026-11-02, plans.md step 18 + *Learn from your own posts* R4; motionlab\monthly.py): a month of
// your posts against your usual, the best ones, what they had in common (a hint), the tests and lessons, ending in
// Claude's three next tests - a picked one goes onto the calendar as an idea
const MN_LEN = () => ({to_30s: t('up to 30 s'), to_60s: t('31–60 s'), to_3min: t('1–3 min'), over_3min: t('over 3 min')});
const MN_GROUP = () => ({pillar: t('By pillar'), length: t('By length'), hook_text: t('Text on screen in the first 3 s')});
const mnMonth = m => { const [y, mo] = m.split('-').map(Number); return new Intl.DateTimeFormat(LANG, {month: 'long', year: 'numeric'}).format(new Date(y, mo - 1, 1)); };
const mnX = x => x == null ? '–' : `${numLoc(x >= 10 ? Math.round(x) : Math.round(x * 10) / 10)}×`;
const mnXc = x => x == null ? '' : x >= 1.5 ? ' up' : x <= 0.67 ? ' down' : '';
const mnGroupVal = (k, v) => k === 'length' ? (MN_LEN()[v] || esc(v)) : k === 'hook_text' ? (v ? t('with text') : t('without text')) : esc(v);
const mnPost = (p, hold) => !p ? '' : `<a class="mnpost" href="${esc(p.url || '#')}" target="_blank" rel="noopener" title="${esc(p.title || '')}">
    <span class="mnth">${p.thumb ? `<img src="${fileUrl(p.thumb)}" loading="lazy" alt="">` : ''}${brandPgLogo(p.platform)}</span>
    <span class="mnpt">${esc(p.title || p.key)}</span>
    <span class="mnpn">${hold ? `<b>${rtPct(p.m.hold_3s)}</b><span class="small dim">${t('at 3 s')}</span>` : `<b>${agNum(p.views)}</b>${p.young
      ? `<span class="extt" title="${ta('Still growing - not compared yet')}">${tn(p.age_days, '{n} day at the check', '{n} days at the check')}</span>`
      : p.x_usual != null ? `<span class="mnx${mnXc(p.x_usual)}" title="${ta('against your usual views')}">${mnX(p.x_usual)}</span>` : ''}`}</span></a>`;
const mnGroups = G => G.map(g => { const max = Math.max(1, ...g.rows.map(r => r.median_x || 0));
  return `<div class="mngrp"><h4>${MN_GROUP()[g.key] || esc(g.key)}</h4>${g.rows.map(r => `<div class="mngr"><span class="mngl">${mnGroupVal(g.key, r.value)}</span>
    <span class="mngb"><i class="${mnXc(r.median_x)}" style="width:${Math.max(3, 100 * Math.log1p(r.median_x || 0) / Math.log1p(max)).toFixed(0)}%"></i></span>
    <b>${mnX(r.median_x)}</b><span class="small dim">${tn(r.n, '{n} post', '{n} posts')}</span></div>`).join('')}</div>`; }).join('');
const mnRes = x => x.result === 'winner' ? `<span class="exres win" style="--vc: ${EXC[x.winner]}">${t('{v} is ahead by your rule', {v: esc(x.winner)})}</span>`
  : x.result === 'too_close' ? `<span class="exres close">${t('Too close to call')}</span>` : `<span class="exres wait">${t('Waiting for numbers')}</span>`;
const mnSt = s => { const a = AG_STATUS.find(x => x[0] === s);
  return a ? `<span class="exst" style="--sc: var(${a[2]})">${a[1]}</span>` : `<span class="exst" style="--sc: var(--dim)">${t('removed from your calendar')}</span>`; };
// several retention curves in one graph, each in its version's colour
function exCurves(series) {
  const w = 600, h = 140, pad = 4, end = Math.max(1, ...series.map(s => +s.end_s || 1));
  const max = Math.max(100, ...series.flatMap(s => s.points.map(p => p[1] || 0)));
  const X = s => pad + (w - 2 * pad) * s / end, Y = p => pad + (h - 2 * pad) * (1 - p / max);
  const lines = series.map(s => { const segs = []; let cur = [];
    s.points.forEach(([x, p]) => { if (p == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push(`${X(x).toFixed(1)},${Y(p).toFixed(1)}`); });
    if (cur.length) segs.push(cur);
    return segs.map(sg => `<polyline points="${sg.join(' ')}" style="stroke: ${EXC[s.id]}"/>`).join(''); }).join('');
  return `<svg class="rtsvg excurves" viewBox="0 0 ${w} ${h}">${[0, 50, 100].map(p => `<line class="rtgrid" x1="${pad}" x2="${w - pad}" y1="${Y(p).toFixed(1)}" y2="${Y(p).toFixed(1)}"/><text class="rtax" x="${pad + 2}" y="${(Y(p) - 3).toFixed(1)}">${p} %</text>`).join('')}${lines}</svg>`;
}
async function pageAgency(main, tabArg) {
  const [CAL, PS, SOC, BRD, TESTS] = await Promise.all([api('/api/agency'), api('/api/projects').catch(() => []),
    api('/api/agency/social').catch(() => ({pages: {}})), brandData(), api('/api/agency/tests').catch(() => ({tests: []}))]);
  CAL.rhythm = CAL.rhythm || {days: [], time: ''}; CAL.posts = CAL.posts || [];
  const PIL = ((BRD || {}).pillars || []).map(x => x.name).filter(Boolean);       // My Brand's content pillars
  const vids = (PS || []).slice().sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));
  const today = new Date(); today.setHours(0, 0, 0, 0);
  let month = new Date(today.getFullYear(), today.getMonth(), 1), queue = Promise.resolve();
  const say = (txt, cls) => { const s = $('#agsaved', main); if (s) { s.className = 'small ' + cls; s.textContent = txt; } };
  const save = () => {
    const body = JSON.parse(JSON.stringify(CAL));
    queue = queue.then(() => api('/api/agency', body).then(r => { CAL.posts = r.posts; say(t('saved ✓'), 'ok'); },
                                                          e => { say(t('NOT saved'), 'bad'); toast(e.message, 'err'); }));
    return queue;
  };
  const nextId = () => 'c' + (Math.max(0, ...CAL.posts.map(p => +String(p.id || '').slice(1) || 0)) + 1);
  const tab0 = AG_TABS.some(([k]) => k === tabArg) ? tabArg : 'calendar';
  main.innerHTML = `<div class="head"><div><h1>${t('Content agency')}</h1><div class="sub">${t('When and where your videos go out - planned in one place.')}</div></div>
      <span id="agsaved" class="small muted"></span></div>
    <div class="tabs brtabs">${AG_TABS.map(([k, l, ic]) => `<a href="#/agency${k === 'calendar' ? '' : '/' + k}" data-tab="${k}"><svg class="i"><use href="#${ic}"/></svg>${l}</a>`).join('')}</div>
    <div class="agpane" data-pane="videos" hidden id="agvids"></div>
    <div class="agpane" data-pane="tests" hidden id="agtests"></div>
    <div class="agpane" data-pane="learn" hidden id="aglearn"></div>
    <div class="agpane" data-pane="month" hidden id="agrev"></div>
    <div class="agpane" data-pane="calendar">
    <div class="agbar"><button class="btn sm ghost icon" id="agprev" title="${ta('The month before')}">‹</button><b class="agmonth" id="agmonth"></b>
      <button class="btn sm ghost icon" id="agnext" title="${ta('The month after')}">›</button><button class="btn sm ghost" id="agtoday">${t('Today')}</button>
      <span class="agweek" id="agweek"></span><span class="grow"></span>
      <button class="btn pri" id="agnew"><svg class="i"><use href="#i-plus"/></svg>${t('New post')}</button>
      <a class="btn" id="agics" href="/api/agency/calendar.ics" download title="${ta('Your dated posts as a calendar file - open it and Windows Calendar, Outlook or Google Calendar reminds you 1 hour before each')}"><svg class="i"><use href="#i-calendar"/></svg>${t('Add to Windows Calendar')}</a></div>
    <div class="agrhythm"><span class="small muted">${t('I post on')}</span><span class="agdays" id="agdays">${AG_DAYS.map((d, i) => `<button class="brpill" data-d="${d}">${esc(agWeekday(i))}</button>`).join('')}</span>
      <span class="small muted">${t('at')}</span><input type="time" id="agtime">
      <span class="small muted agrh">${t('Your rhythm - the empty days show as dashed slots. Posting regularly matters more than the hour.')}</span>
      <button class="btn sm ghost" id="agwhen" title="${ta('Your own best hours per platform, from your stats')}"><svg class="i"><use href="#i-clock"/></svg>${t('When to post')}</button></div>
    <div class="aggrid"><div class="agcal"><div class="agwd">${AG_DAYS.map((d, i) => `<span>${esc(agWeekday(i))}</span>`).join('')}</div><div class="agcells" id="agcells"></div>
        <div class="aglegend">${AG_STATUS.map(([, l, c]) => `<span><i style="background: var(${c})"></i>${l}</span>`).join('')}</div>
        <div class="agbal" id="agbal"></div></div>
      <div class="panel agideas" data-drop=""><h2>${t('Ideas')} <span class="dim" id="agidn"></span></h2>
        <div class="small muted">${t('Posts without a day yet - drag one onto the calendar.')}</div><div id="agidl"></div>
        <button class="btn sm" id="agidea"><svg class="i"><use href="#i-plus"/></svg>${t('Add an idea')}</button></div></div></div>`;
  const showTab = k => {
    $$('.brtabs a', main).forEach(a => a.classList.toggle('on', a.dataset.tab === k));
    $$('.agpane', main).forEach(p => { p.hidden = p.dataset.pane !== k; });
  };
  $$('.brtabs a', main).forEach(a => a.onclick = e => { e.preventDefault(); showTab(a.dataset.tab); history.replaceState(null, '', a.getAttribute('href'));
    if (a.dataset.tab === 'learn') drawLearn();                     // read when first opened (R3)
    if (a.dataset.tab === 'month') drawMonth(); });                 // (R4)
  showTab(tab0);
  // your posted videos (2026-10-26): every video the last Check my pages found, with the page's median views (to say
  // which did better than usual) and its views at earlier checks (how it grew)
  const pageVids = Object.entries(SOC.pages || {}).flatMap(([plat, pg]) => (pg.videos || []).map(v => ({...v, platform: plat})));
  // 0.6.0 step 13: the stats files you imported - their numbers on the videos read from your pages (by id), the rest
  // (Instagram, and videos older than a check reaches) as cards of their own
  const impRows = Object.entries((SOC.stats || {}).videos || {}).flatMap(([plat, rows]) => Object.values(rows).map(r => ({...r, platform: plat, imported: true})));
  pageVids.forEach(v => { v.imp = impRows.find(r => r.platform === v.platform && r.id && String(r.id) === String(v.id)); });
  const impOnly = impRows.filter(r => !pageVids.some(v => v.imp === r));
  const medians = Object.fromEntries(Object.entries(SOC.pages || {}).map(([plat, pg]) => {
    const vs = (pg.videos || []).map(v => v.views).filter(v => v != null).sort((a, b) => a - b);
    return [plat, vs.length >= 3 ? vs[Math.floor(vs.length / 2)] : null]; }));
  const liveByDay = {};
  pageVids.filter(v => v.date).forEach(v => (liveByDay[v.date] = liveByDay[v.date] || []).push(v));
  const chip = p => { const st = AG_STATUS.find(s => s[0] === p.status) || AG_STATUS[0];
    return `<div class="agchip st-${p.status}" draggable="true" data-id="${esc(p.id)}" style="--sc: var(${st[2]})" title="${esc(p.title)} · ${esc(st[1])}">
      <i class="agst"></i>${p.next ? '<svg class="i agnx"><use href="#i-ab"/></svg>' : ''}${(p.platforms || []).slice(0, 3).map(x => `<img src="/files/logos/${x}/color.svg" alt="">`).join('')}
      <span class="agct">${esc(p.title)}</span>${p.time ? `<span class="agtm">${esc(p.time)}</span>` : ''}</div>`; };
  const paintRhythm = () => {
    $$('#agdays .brpill', main).forEach(b => b.classList.toggle('on', CAL.rhythm.days.includes(b.dataset.d)));
    $('#agtime', main).value = CAL.rhythm.time || '';
  };
  const paint = () => {
    $('#agmonth', main).textContent = new Intl.DateTimeFormat(LANG, {month: 'long', year: 'numeric'}).format(month);
    const first = new Date(month), lead = (first.getDay() + 6) % 7;                 // Monday first
    const start = new Date(first); start.setDate(1 - lead);
    const byDay = {};
    CAL.posts.filter(p => p.date).forEach(p => (byDay[p.date] = byDay[p.date] || []).push(p));
    Object.values(byDay).forEach(l => l.sort((a, b) => (a.time || '99').localeCompare(b.time || '99')));
    const cells = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(start); d.setDate(start.getDate() + i);
      if (i >= 35 && d.getMonth() !== month.getMonth()) break;                       // no sixth row of next month
      const iso = agIso(d), posts = byDay[iso] || [], wd = AG_DAYS[(d.getDay() + 6) % 7];
      const slot = !posts.length && CAL.rhythm.days.includes(wd) && d >= today;
      const live = liveByDay[iso] || [];                  // what went up that day on your pages (Check my pages)
      cells.push(`<div class="agcell${d.getMonth() !== month.getMonth() ? ' out' : ''}${+d === +today ? ' today' : ''}${slot && !live.length ? ' slot' : ''}${d < today ? ' past' : ''}" data-drop="${iso}">
        <span class="agdn">${d.getDate()}</span>${posts.map(chip).join('')}
        ${live.map(v => `<a class="aglive" href="${esc(v.url)}" target="_blank" rel="noopener" title="${esc(v.title)} · ${ta('{n} views', {n: agNum(v.views)})}">
          <img src="/files/logos/${v.platform}/color.svg" alt=""><span class="agct">${esc(v.title)}</span><b>${esc(agNum(v.views))}</b></a>`).join('')}
        ${slot && !live.length ? `<span class="agslot">${t('a post here')}</span>` : ''}</div>`);
    }
    $('#agcells', main).innerHTML = cells.join('');
    const ideas = CAL.posts.filter(p => !p.date);
    $('#agidn', main).textContent = ideas.length || '';
    $('#agidl', main).innerHTML = ideas.map(chip).join('') || '';
    // this week: posts planned against the rhythm (Monday to Sunday)
    const ws = new Date(today); ws.setDate(today.getDate() - (today.getDay() + 6) % 7);
    const we = new Date(ws); we.setDate(ws.getDate() + 6);
    // the days of this week with something planned or posted (a video your pages show counts too), against the rhythm
    const inWeek = new Set([...CAL.posts.filter(p => p.date).map(p => p.date), ...Object.keys(liveByDay)]
      .filter(d => agDay(d) >= ws && agDay(d) <= we)).size;
    $('#agweek', main).innerHTML = CAL.rhythm.days.length ? `${t('This week')}: <b>${inWeek}</b> / ${CAL.rhythm.days.length}` : '';
    // the month's balance between your pillars (My Brand's content pillars)
    const ym = `${month.getFullYear()}-${pad(month.getMonth() + 1)}`, inMonth = CAL.posts.filter(p => (p.date || '').startsWith(ym));
    $('#agbal', main).innerHTML = PIL.length && inMonth.length ? `${t('This month by pillar')}: ${[...PIL, ''].map(n => {
      const k = inMonth.filter(p => (p.pillar || '') === n).length;
      return k || n ? `<span class="${k ? '' : 'zero'}">${n ? `<b>${esc(n)}</b>` : t('no pillar')} ${k}</span>` : ''; }).filter(Boolean).join(' · ')}` : '';
    $$('.agchip', main).forEach(c => {
      c.onclick = e => { e.stopPropagation(); const p = CAL.posts.find(x => x.id === c.dataset.id); if (p) agPostModal(p); };
      c.ondragstart = e => { e.dataTransfer.setData('text/plain', c.dataset.id); c.classList.add('drag'); };
      c.ondragend = () => c.classList.remove('drag');
    });
    $$('[data-drop]', main).forEach(z => {
      z.ondragover = e => { e.preventDefault(); z.classList.add('over'); };
      z.ondragleave = () => z.classList.remove('over');
      z.ondrop = e => { e.preventDefault(); z.classList.remove('over');
        const p = CAL.posts.find(x => x.id === e.dataTransfer.getData('text/plain'));
        if (p && p.date !== z.dataset.drop) { p.date = z.dataset.drop; if (!p.date) p.time = ''; else if (!p.time && CAL.rhythm.time) p.time = CAL.rhythm.time;
          paint(); save(); } };
    });
    $$('.agcell', main).forEach(c => c.onclick = e => { if (e.target.closest('.aglive')) return;
      agPostModal({id: '', title: '', date: c.dataset.drop, time: CAL.rhythm.time || '', platforms: [], status: 'idea', project: '', notes: '', sound: '', links: {}}); });
  };
  // a post's pop-up: new (id '') or one of the calendar's
  const agPostModal = p0 => {
    const p = JSON.parse(JSON.stringify(p0)), isNew = !p.id;
    const vidOpt = v => `<option value="${esc(v.name)}"${p.project === v.name ? ' selected' : ''}>${esc(pname(v))}</option>`;
    modal(`<h2>${isNew ? t('New post') : t('Post')}</h2>
      <div class="agform">
        <label class="agf wide"><span>${t('What it is')}</span><input type="text" id="agt" maxlength="120" value="${esc(p.title)}" placeholder="${ta('e.g. Behind the scenes of the 4AM video')}"></label>
        <label class="agf"><span>${t('Day')}</span><input type="date" id="agd" value="${esc(p.date)}"></label>
        <label class="agf"><span>${t('Time')}</span><input type="time" id="agh" value="${esc(p.time)}"><span class="agbest" id="agbest"></span></label>
        <div class="agf wide"><span>${t('Where')}</span><div class="agplats">${Object.keys(BRAND_PAGES).map(x => `<button class="brpgb${p.platforms.includes(x) ? ' on' : ''}" data-p="${x}" title="${esc(BRAND_PAGES[x])}">${brandPgLogo(x)}</button>`).join('')}</div></div>
        <div class="agf wide"><span>${t('Stage')}</span><div class="brpills agsts">${AG_STATUS.map(([s, l, c]) => `<button class="brpill${p.status === s ? ' on' : ''}" data-s="${s}" style="--sc: var(${c})"><i class="agst"></i>${l}</button>`).join('')}</div></div>
        ${PIL.length ? `<div class="agf wide"><span>${t('Pillar')}</span><div class="brpills agpil">${PIL.map(n => `<button class="brpill${p.pillar === n ? ' on' : ''}" data-pl="${esc(n)}">${esc(n)}</button>`).join('')}</div></div>` : ''}
        <label class="agf wide"><span>${t('The video')}</span><span class="agvid"><span class="agvp" id="agvp"></span>
          <select id="agv"><option value="">${t('None yet')}</option>${vids.map(vidOpt).join('')}</select></span></label>
        <label class="agf wide"><span>${t('Sound to add in the app')}</span><input type="text" id="ags" maxlength="200" value="${esc(p.sound)}" placeholder="${ta('a trending sound - added in TikTok / Instagram when you post, never in the video')}"></label>
        <label class="agf wide"><span>${t('Notes')}</span><textarea id="agn" rows="2" maxlength="1000">${esc(p.notes)}</textarea></label>
        <div class="agf wide" id="aglinks"></div>
        <div class="agf wide" id="agdid"></div>
        <label class="agf wide" id="agabw"><span>${t('Test & compare winner (YouTube)')}</span><input type="text" id="agab" maxlength="120" value="${esc(p.ab || '')}" placeholder="${ta('e.g. B - the red thumbnail, 54 %')}"></label>
        <div class="agf wide" id="agcl"></div>
      </div>
      <div class="row" style="margin-top:14px"><button class="btn pri" id="agok">${t('Save')}</button><button class="btn ghost" id="agno">${t('Cancel')}</button>
        <span class="grow"></span>${isNew ? '' : `<button class="btn danger" id="agdel">${t('Delete')}</button>`}</div>`, m => {
      const links = () => {
        $('#aglinks', m).innerHTML = p.platforms.length ? `<span>${t('Where it went up')}</span>${p.platforms.map(x => `<label class="aglink">${brandPgLogo(x)}<input type="url" data-l="${x}" value="${esc((p.links || {})[x] || '')}" placeholder="${ta('Link to the post on {platform}', {platform: BRAND_PAGES[x]})}"></label>`).join('')}` : '';
      };
      const vprev = () => { const v = vids.find(x => x.name === $('#agv', m).value);
        $('#agvp', m).innerHTML = v && v.picture ? `<img src="${picUrl(v.picture)}" alt="">` : '<svg class="i"><use href="#i-film"/></svg>'; };
      p.checks = p.checks || {};
      const vidOf = () => vids.find(x => x.name === $('#agv', m).value);
      const extras = () => {                                // the best times, how it did, the checklist and the shapes
        const best = [...new Set(p.platforms.flatMap(x => (CAL.when || {})[x] || []))];
        $('#agbest', m).innerHTML = best.map(b => `<button class="brpill" data-bt="${esc(b)}" title="${ta('Your best time')}">${esc(agWhenLabel(b))}</button>`).join('');
        $$('[data-bt]', m).forEach(b => b.onclick = e => { e.preventDefault(); $('#agh', m).value = b.dataset.bt.split(' ')[1]; });
        $('#agabw', m).hidden = !p.platforms.includes('youtube');
        const did = p.platforms.map(x => agHowItDid(x, ((p.links || {})[x]) || ($(`[data-l=${x}]`, m) || {}).value, SOC, pageVids)).filter(Boolean);
        $('#agdid', m).innerHTML = did.length ? `<span>${t('How it did')}</span><div class="agdid">${did.join('')}</div>` : '';
        const C = AG_CHECKS(), items = p.platforms.length ? [...C.all.map(([k, l]) => ['all', k, l]), ...p.platforms.flatMap(x => (C[x] || []).map(([k, l]) => [x, k, l]))]
          .filter(([pl, k]) => k !== 'sound' || p.sound || $('#ags', m).value.trim()) : [];
        const done = items.filter(([pl, k]) => p.checks[`${pl}:${k}`]).length, v = vidOf(), L = v && v.latest;
        const shape = L && L.width ? (L.width > L.height * 1.15 ? '16:9' : L.height > L.width * 1.15 ? '9:16' : '1:1') : '';
        const off = shape ? p.platforms.filter(x => AG_SHAPE[x] && AG_SHAPE[x][0] !== shape && !(x === 'youtube' && shape === '9:16')) : [];
        $('#agcl', m).innerHTML = items.length ? `<span>${t('Before you post')} <b class="agdone">${done} / ${items.length}</b></span>
          <div class="agchks">${items.map(([pl, k, l]) => `<label class="agck"><input type="checkbox" data-ck="${pl}:${k}"${p.checks[`${pl}:${k}`] ? ' checked' : ''}>${pl === 'all' ? '' : brandPgLogo(pl)}<span>${esc(l)}</span></label>`).join('')}</div>
          ${p.platforms.length ? `<div class="small muted agshape">${t('Formats')}: ${p.platforms.map(x => `${esc(BRAND_PAGES[x] || x)} ${esc((AG_SHAPE[x] || ['', '?'])[1])}`).join(' · ')}${shape
            ? ` - ${t('your video is {shape}', {shape})}${off.length ? `: ${t('make a {shape} version for {where} (New edit with the same clips, its Format step)', {shape: AG_SHAPE[off[0]][0], where: off.map(x => BRAND_PAGES[x] || x).join(', ')})}` : ' ✓'}` : ''}</div>` : ''}` : '';
        $$('[data-ck]', m).forEach(c => c.onchange = () => { if (c.checked) p.checks[c.dataset.ck] = true; else delete p.checks[c.dataset.ck];
          $('.agdone', m).textContent = `${Object.keys(p.checks).filter(k => items.some(([pl, kk]) => `${pl}:${kk}` === k)).length} / ${items.length}`; });
      };
      links(); vprev(); extras();
      $('#ags', m).addEventListener('input', debounce(extras, 300));
      $('#aglinks', m).addEventListener('change', extras);
      $$('.agplats .brpgb', m).forEach(b => b.onclick = () => { const x = b.dataset.p;
        p.platforms = p.platforms.includes(x) ? p.platforms.filter(y => y !== x) : [...p.platforms, x]; b.classList.toggle('on'); links(); extras(); });
      $$('.agsts .brpill', m).forEach(b => b.onclick = () => { p.status = b.dataset.s; $$('.agsts .brpill', m).forEach(x => x.classList.toggle('on', x === b)); });
      $$('.agpil .brpill', m).forEach(b => b.onclick = () => { p.pillar = p.pillar === b.dataset.pl ? '' : b.dataset.pl;
        $$('.agpil .brpill', m).forEach(x => x.classList.toggle('on', x.dataset.pl === p.pillar)); });
      $('#agv', m).onchange = () => { vprev(); extras(); };
      $('#agno', m).onclick = closeModal;
      if (!isNew) $('#agdel', m).onclick = async () => { CAL.posts = CAL.posts.filter(x => x.id !== p.id); closeModal(); paint(); await save(); };
      $('#agok', m).onclick = async () => {
        p.title = $('#agt', m).value.trim();
        if (!p.title) { toast(t('Say what the post is first'), 'err'); $('#agt', m).focus(); return; }
        Object.assign(p, {date: $('#agd', m).value, time: $('#agh', m).value, project: $('#agv', m).value, sound: $('#ags', m).value.trim(), ab: $('#agab', m).value.trim(),
                          notes: $('#agn', m).value.trim(), links: Object.fromEntries($$('[data-l]', m).map(i => [i.dataset.l, i.value.trim()]).filter(([, v]) => v))});
        if (isNew) { p.id = nextId(); CAL.posts.push(p); } else Object.assign(CAL.posts.find(x => x.id === p.id), p);
        const ok = await save().then(() => true, () => false);
        if (ok) { closeModal(); paint(); }
      };
      if (isNew) $('#agt', m).focus();
    }, 'agmodal');
  };
  $('#agprev', main).onclick = () => { month = new Date(month.getFullYear(), month.getMonth() - 1, 1); paint(); };
  $('#agnext', main).onclick = () => { month = new Date(month.getFullYear(), month.getMonth() + 1, 1); paint(); };
  $('#agtoday', main).onclick = () => { month = new Date(today.getFullYear(), today.getMonth(), 1); paint(); };
  $$('#agdays .brpill', main).forEach(b => b.onclick = () => { const d = b.dataset.d;
    CAL.rhythm.days = CAL.rhythm.days.includes(d) ? CAL.rhythm.days.filter(x => x !== d) : AG_DAYS.filter(x => x === d || CAL.rhythm.days.includes(x));
    paintRhythm(); paint(); save(); });
  $('#agtime', main).onchange = e => { CAL.rhythm.time = e.target.value; save(); };
  $('#agwhen', main).onclick = () => {                     // 0.6.0 step 16: your best times, typed from your stats
    const plats = [...new Set([...((BRD || {}).pages || []).filter(p => p.url).map(p => p.platform), ...Object.keys(CAL.when || {})])];
    const list = plats.length ? plats : ['youtube', 'tiktok', 'instagram'];
    CAL.when = CAL.when || {};
    const W = JSON.parse(JSON.stringify(CAL.when)), GW = AG_WHEN_WHERE(), GG = AG_GENERIC();
    modal(`<h2>${t('When to post')}</h2><p class="hint">${t('Your own audience\'s best hours beat any study - type them from each platform\'s stats. They show as quick picks on every post. Posting regularly still matters more than the hour.')}</p>
      <div class="agwhen" id="agwl"></div><div class="row" style="margin-top:12px"><button class="btn pri" id="agwok">${t('Save')}</button><button class="btn ghost" id="agwno">${t('Cancel')}</button></div>`, mm => {
      const draw = () => { $('#agwl', mm).innerHTML = list.map(x => `<div class="agwrow">${brandPgLogo(x)}<b>${esc(BRAND_PAGES[x] || x)}</b>
          <span class="brpills">${(W[x] || []).map((b, i) => `<span class="brpill on">${esc(agWhenLabel(b))}<button class="brx" data-wx="${x}:${i}" title="${ta('Remove')}">✕</button></span>`).join('')}</span>
          <span class="agwadd"><select data-wd="${x}"><option value="any">${t('Any day')}</option>${AG_DAYS.map((d, i) => `<option value="${d}">${esc(agWeekday(i))}</option>`).join('')}</select>
            <input type="time" data-wt="${x}" value="18:00"><button class="btn sm" data-wa="${x}">${t('Add')}</button></span>
          <span class="small muted agwhere">${(W[x] || []).length ? '' : esc(GG[x] || t('Generic: when your audience is free - the studies disagree.')) + ' '}${GW[x] ? esc(t('Yours: {where}', {where: GW[x]})) : ''}</span></div>`).join('');
        $$('[data-wa]', mm).forEach(b => b.onclick = () => { const x = b.dataset.wa, v = `${$(`[data-wd=${x}]`, mm).value} ${$(`[data-wt=${x}]`, mm).value}`;
          if (!/^\w{3} \d{2}:\d{2}$/.test(v)) return; W[x] = [...new Set([...(W[x] || []), v])].slice(0, 8); draw(); });
        $$('[data-wx]', mm).forEach(b => b.onclick = () => { const [x, i] = b.dataset.wx.split(':'); W[x].splice(+i, 1); if (!W[x].length) delete W[x]; draw(); }); };
      draw();
      $('#agwno', mm).onclick = closeModal;
      $('#agwok', mm).onclick = async () => { CAL.when = W; const ok = await save().then(() => true, () => false); if (ok) closeModal(); };
    });
  };
  const blank = date => ({id: '', title: '', date, time: date ? CAL.rhythm.time || '' : '', platforms: [], status: 'idea', project: '', notes: '', sound: '', pillar: '', links: {}});
  $('#agnew', main).onclick = () => agPostModal(blank(agIso(today)));
  $('#agidea', main).onclick = () => agPostModal(blank(''));
  paintRhythm(); paint();
  // ---- Your videos: the pages My Brand names, Check my pages, the videos as cards
  const pages = ((BRD || {}).pages || []).filter(p => p.url), vbox = $('#agvids', main);
  let sort = 'new', only = '';
  const handle = u => '@' + String(u).replace(/\/+$/, '').split('/').pop().replace(/^@/, '');
  const grew = v => { const h = ((SOC.history || {})[`${v.platform}:${v.id}`] || []); return h.length >= 2 ? {d: h[h.length - 1][1] - h[h.length - 2][1], at: h[h.length - 2][0]} : null; };
  // 2026-11-02: a card = the video (its link), its numbers, where people left (your retention graph, traced) and its SPARK
  const vkey = v => v.id && ['tiktok', 'youtube', 'instagram'].includes(v.platform) ? `${v.platform}:${v.id}` : '';
  const vcard = v => { const m = medians[v.platform], x = m && v.views != null && m > 0 ? v.views / m : null, g = grew(v);
    const key = vkey(v), R = key ? (SOC.retention || {})[key] : null, M = (R && R.summary) || {}, sp = key ? (SOC.spark || {})[key] : null;
    return `<div class="agvc" title="${esc(v.title)}"><a class="agvl" href="${esc(v.url)}" target="_blank" rel="noopener">
      <span class="agvt${v.short ? ' short' : ''}">${v.thumb ? `<img src="${fileUrl(v.thumb)}" loading="lazy" alt="">` : ''}<img class="agvpl" src="/files/logos/${v.platform}/color.svg" alt="">
        ${x != null && x >= 1.5 ? `<em title="${ta('Views against your usual (the median of your page)')}">×${numStr(Math.round(x * 10) / 10)}</em>` : ''}</span>
      <b class="agvn">${esc(v.title || '–')}</b></a>
      <span class="agvs"><span class="agvv">${esc(agNum(v.views))} <small>${t('views')}</small></span>${v.likes != null ? `<span>♥ ${esc(agNum(v.likes))}</span>` : ''}${v.comments != null ? `<span>💬 ${esc(agNum(v.comments))}</span>` : ''}</span>
      <span class="small muted">${v.date ? esc(whenStr(v.date + (v.time ? ' ' + v.time : ''))) : t('date unknown')}${g && g.d > 0 ? ` · <span class="agup">+${esc(agNum(g.d))} ${t('since {when}', {when: esc(whenWords(g.at))})}</span>` : ''}</span>
      ${agImpLine(v.imported ? v : v.imp)}
      ${R ? `<button class="agret" data-rt="${esc(key)}" title="${ta('Where people left - your retention graph, read by MotionLab. Click to change it.')}">${retSvg(R.points || [], R.end_s, {mini: true, w: 200, h: 34, drops: (M.drops || []).slice(0, 1)})}
          <span>${t('3 s')} <b>${rtPct(M.hold_3s)}</b>${M.hold_10s != null ? ` · ${t('10 s')} <b>${rtPct(M.hold_10s)}</b>` : ''} · ${t('end')} <b>${rtPct(M.end)}</b></span></button>` : ''}
      ${key ? `<div class="agvact">${R ? '' : `<button class="btn sm ghost" data-rt="${esc(key)}" title="${ta('Paste a screenshot of its retention graph - MotionLab reads where people left')}"><svg class="i"><use href="#i-retention"/></svg>${t('Where people left')}</button>`}
        ${sp ? `<a class="btn sm ghost" href="#/spark/${encodeURIComponent(sp.name)}"><svg class="i"><use href="#i-sparkle"/></svg>${sp.status === 'ready' ? t('Why it worked') : t('SPARK - waiting for Claude')}</a>`
          : v.url && v.url !== '#' ? `<button class="btn sm ghost" data-spk="${esc(v.url)}" title="${ta("Why this video worked: its hook, its story and its numbers against the creator's usual")}"><svg class="i"><use href="#i-sparkle"/></svg>SPARK</button>` : ''}</div>` : ''}</div>`; };
  const drawVids = () => {
    const readable = pages.filter(p => ['youtube', 'tiktok'].includes(p.platform)), other = pages.filter(p => !['youtube', 'tiktok'].includes(p.platform));
    const list = [...pageVids, ...impOnly.map(r => ({...r, url: r.url || '#'}))].filter(v => !only || v.platform === only)
      .sort((a, b) => sort === 'views' ? (b.views ?? -1) - (a.views ?? -1) : `${b.date} ${b.time}`.localeCompare(`${a.date} ${a.time}`));
    vbox.innerHTML = !pages.length ? `<div class="agvempty"><svg class="i"><use href="#i-link"/></svg><b>${t('Add your pages first')}</b>
        <span class="small muted">${t('My Brand > Overview > Your pages - your YouTube and TikTok; then Check my pages brings in your videos with their views.')}</span>
        <a class="btn pri" href="#/brand">${t('Open My Brand')}</a></div>`
      : `<div class="agvtop"><div class="agpgs">${pages.map(p => { const pg = (SOC.pages || {})[p.platform] || {};
          return `<div class="agpg${only === p.platform ? ' on' : ''}" data-p="${p.platform}">${brandPgLogo(p.platform)}<span><b>${esc(handle(p.url))}</b>
            <small>${!['youtube', 'tiktok'].includes(p.platform) ? t('not read here yet') : pg.error ? esc(pg.error) : (pg.videos || []).length
              ? `${pg.followers != null ? `${esc(agNum(pg.followers))} ${t('followers')} · ` : ''}${tn(pg.videos.length, '{n} video', '{n} videos')}` : t('not checked yet')}</small></span></div>`; }).join('')}</div>
        <div class="agchkw">${readable.length ? `<button class="btn pri brimpbig" id="agchk" title="${ta('Reads your own public pages now - only when you press it, no login')}"><svg class="i"><use href="#i-update"/></svg><span>${t('Check my pages')}</span></button>
          <div class="brprog" id="agprog" hidden><i></i></div><div class="small muted" id="agchkst"></div>` : ''}
          <label class="btn" title="${ta('The file you downloaded from YouTube Studio (Advanced mode > Export), TikTok Studio or Meta Business Suite (Insights > Export) - views, watch time, retention')}"><svg class="i"><use href="#i-upload"/></svg>${t('Import your stats')}<input type="file" id="agimp" hidden accept=".csv,.xlsx,.zip,.tsv"></label></div></div>
        ${other.length ? `<div class="small muted agvnote">${t('Instagram and the other pages need a login to be read - import the file you download from them (Import your stats).')}</div>` : ''}
        ${(SOC.stats || {}).imports && SOC.stats.imports.length ? `<div class="small muted agvnote">${t('Imported: {files}', {files: SOC.stats.imports.slice(-3).map(x => `${BRAND_PAGES[x.platform] || x.platform} (${x.rows}, ${whenStr(x.date)})`).join(' · ')})}</div>` : ''}
        ${pageVids.length || impOnly.length ? `<div class="agvbar"><span class="brpills">${[['new', t('Newest')], ['views', t('Most viewed')]].map(([k, l]) => `<button class="brpill${sort === k ? ' on' : ''}" data-s="${k}">${l}</button>`).join('')}</span></div>
          <div class="agvgrid">${list.map(vcard).join('')}</div>` : readable.length ? `<div class="agvempty"><svg class="i"><use href="#i-film"/></svg><b>${t('No videos read yet')}</b>
          <span class="small muted">${t('Press Check my pages - your newest videos come in with when they were posted, their views, likes and comments.')}</span></div>` : ''}`;
    const st = $('#agchkst', vbox);
    if (st) st.dataset.idle = SOC.checked ? t('Checked {when}', {when: whenStr(SOC.checked)}) : t('Never checked yet');
    agCheckPaint();
    const chk = $('#agchk', vbox);
    if (chk) chk.onclick = async () => {
      let j; try { j = await api('/api/jobs', {kind: 'agency_check', args: {}, queue: true}); } catch (e) { toast(e.message, 'err'); return; }
      agCheckWatch(j.id);
    };
    $$('.agpg', vbox).forEach(p => p.onclick = () => { only = only === p.dataset.p ? '' : p.dataset.p; drawVids(); });
    $$('[data-rt]', vbox).forEach(b => b.onclick = () => { const key = b.dataset.rt, v = list.find(x => vkey(x) === key) || {};
      retentionModal({key, url: v.url, title: v.title, duration: v.duration, platform: v.platform, entry: (SOC.retention || {})[key]},
        e => { SOC.retention = SOC.retention || {}; if (e) SOC.retention[key] = e; else delete SOC.retention[key]; drawVids(); }); });
    $$('[data-spk]', vbox).forEach(b => b.onclick = () => addSparkModal([], [b.dataset.spk]));
    const imp = $('#agimp', vbox);
    if (imp) imp.onchange = async () => { const f = imp.files[0]; imp.value = ''; if (f) agImport(f, ''); };
    $$('.agvbar [data-s]', vbox).forEach(b => b.onclick = () => { sort = b.dataset.s; drawVids(); });
  };
  // a stats file in: its platform guessed (else asked), then the page again with its numbers
  const agImport = (f, platform) => new Promise(done => { const x = new XMLHttpRequest();
    x.open('POST', `/api/agency/stats?name=${encodeURIComponent(f.name)}&platform=${platform}`); x.setRequestHeader('X-ML-Token', TOKEN);
    x.setRequestHeader('Content-Type', 'application/octet-stream');
    x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (e) { /* not JSON */ }
      if (x.status < 300) { toast(tn(j.rows, '{n} video from your {platform} file ({new} new)', '{n} videos from your {platform} file ({new} new)', {platform: BRAND_PAGES[j.platform] || j.platform, new: j.new}), 'ok'); route(true); }
      else if (!platform && j && /platform|plataforma/i.test(j.error || '')) {
        modal(`<h2>${t('Which platform is it from?')}</h2><div class="agplats">${Object.keys(BRAND_PAGES).map(p2 => `<button class="brpgb" data-ip="${p2}">${brandPgLogo(p2)}</button>`).join('')}</div>`, mm => {
          $$('[data-ip]', mm).forEach(b => b.onclick = () => { closeModal(); agImport(f, b.dataset.ip); }); });
      } else toast((j && j.error) || x.status, 'err');
      done(); };
    x.onerror = () => { toast(t('{name}: the copy stopped - try again', {name: f.name}), 'err'); done(); };
    x.send(f); });
  drawVids();
  // ---- Tests (R2): the list as cards; a test's pop-up = its versions, numbers, curves, rule, result, Claude's review
  const tbox = $('#agtests', main);
  let TS = TESTS || {tests: []};
  const exTitle = id => ((TS.tests || []).find(x => x.id === id) || {}).title || id;
  const exCard = T => { const [sl, sc] = EX_STATE()[T.state] || ['', '--dim'];
    return `<div class="excard" data-xid="${esc(T.id)}"><div class="exch"><span class="exst" style="--sc: var(${sc})">${sl}</span>${brandPgLogo(T.platform)}<b>${esc(T.title)}</b></div>
      <div class="exvs">${T.versions.map(v => `<div class="exv${(T.result || {}).winner === v.id ? ' win' : ''}" style="--vc: ${EXC[v.id]}">
        <span class="exvt">${v.thumb ? `<img src="${fileUrl(v.thumb)}" loading="lazy" alt="">` : ''}<i>${v.id}</i></span>
        <span class="small exvl">${esc(v.label || v.title || (v.link ? t('posted') : t('not posted yet')))}</span>
        <b>${exVal(T.rule.metric, (v.numbers || {})[T.rule.metric])}</b></div>`).join('')}</div>
      <div class="small muted exm">${esc(EX_METRIC()[T.rule.metric] || '')} · ${exResLine(T)}</div>
      ${T.parent ? `<div class="small dim">${t('a follow-up of “{title}”', {title: esc(exTitle(T.parent))})}</div>` : ''}</div>`; };
  const reload = async open => {
    try { TS = await api('/api/agency/tests'); } catch (e) { toast(e.message, 'err'); return; }
    drawTests();
    const x = open && TS.tests.find(y => y.id === open);
    if (x) exModal(x);
  };
  const drawTests = () => {
    const list = TS.tests || [];
    tbox.innerHTML = `<div class="exbar"><button class="btn pri" data-exnew><svg class="i"><use href="#i-plus"/></svg>${t('New test')}</button>
        <span class="small muted">${t('Two versions of one idea on the same platform - which one did better by the number you pick? One post each is a hint, never proof.')}</span></div>
      ${list.length ? `<div class="exgrid">${list.map(exCard).join('')}</div>` : `<div class="agvempty"><svg class="i"><use href="#i-ab"/></svg><b>${t('No tests yet')}</b>
        <span class="small muted">${t('Post two versions of one idea - another hook, another length - and compare them here.')}</span><button class="btn pri" data-exnew>${t('New test')}</button></div>`}`;
    $$('[data-exnew]', tbox).forEach(b => b.onclick = () => exModal(blankTest()));
    $$('.excard', tbox).forEach(c => c.onclick = () => { const x = TS.tests.find(y => y.id === c.dataset.xid); if (x) exModal(x); });
  };
  const blankTest = () => ({id: '', title: '', change: '', parent: '', state: 'planned',
    platform: (pages.find(p => ['tiktok', 'youtube', 'instagram'].includes(p.platform)) || {}).platform || 'tiktok',
    rule: {metric: '', min_views: TS.min_views || 1000},
    versions: ['A', 'B'].map(id => ({id, label: '', link: '', project: '', render: ''}))});
  const exModal = T0 => {
    const T = JSON.parse(JSON.stringify(T0)), isNew = !T.id, closed = !!T.decision, dis = closed ? ' disabled' : '';
    if (!T.rule.metric) T.rule.metric = T.platform === 'instagram' ? 'hold_3s' : 'views_7d';
    const st = EX_STATE()[T.state] || ['', '--dim'];
    modal(`<h2 class="exh"><svg class="i"><use href="#i-ab"/></svg><span>${isNew ? t('New test') : esc(T.title)}</span>${isNew ? '' : `<span class="exst" style="--sc: var(${st[1]})">${st[0]}</span>`}</h2>
      ${T.parent ? `<div class="small dim">${t('a follow-up of “{title}”', {title: esc(exTitle(T.parent))})}</div>` : ''}
      <div class="agform">
        <label class="agf wide"><span>${t('What you are testing')}</span><input type="text" id="ext" maxlength="120" value="${esc(T.title)}" placeholder="${ta('e.g. Handstand tutorial: a question as the hook')}"${dis}></label>
        <label class="agf wide"><span>${t('The one thing that differs')}</span><input type="text" id="exc" maxlength="300" value="${esc(T.change)}" placeholder="${ta('e.g. B opens with a question instead of the result')}"${dis}></label>
        <div class="agf wide"><span>${t('Where they went up')}</span><div class="agplats">${['tiktok', 'youtube', 'instagram'].map(x => `<button class="brpgb${T.platform === x ? ' on' : ''}" data-xp="${x}"${dis}>${brandPgLogo(x)}</button>`).join('')}</div></div>
      </div>
      <div class="exvgrid" id="exvg"></div><div id="excv"></div>
      <div class="exrule"><span>${t('Decided by')}</span><select id="exm"${dis}>${Object.entries(EX_METRIC()).map(([k, l]) => `<option value="${k}"${T.rule.metric === k ? ' selected' : ''}>${esc(l)}</option>`).join('')}</select>
        <span>${t('with at least')}</span><input type="number" id="exmv" min="0" step="100" value="${esc(T.rule.min_views)}"${dis}><span>${t('views each')}</span></div>
      <div class="small muted">${t('Pick the number before the results are in, and change one thing at a time.')}</div>
      ${isNew ? '' : `<div class="exresult">${exResLine(T)}<span class="small muted">${t('One post each - other days, other audiences. Repeat it before you trust it.')}</span></div>`}
      <div id="exrev"></div><div id="exclose"></div>
      <div class="row" style="margin-top:14px" id="exact"></div>`, m => {
      const plVids = () => pageVids.filter(v => v.platform === T.platform).sort((a, b) => `${b.date} ${b.time}`.localeCompare(`${a.date} ${a.time}`));
      const vgrid = () => {
        $('#exvg', m).innerHTML = T.versions.map((v, i) => `<div class="exvcol" style="--vc: ${EXC[v.id]}">
          <div class="exvh"><i>${v.id}</i><input type="text" data-vl="${i}" maxlength="60" value="${esc(v.label || '')}" placeholder="${i ? ta('e.g. the question hook') : ta('e.g. the control')}"${dis}>${!closed && i >= 2 ? `<button class="brx" data-vx="${i}" title="${ta('Remove')}">✕</button>` : ''}</div>
          <span class="exvt big">${v.thumb ? `<img src="${fileUrl(v.thumb)}" alt="">` : '<svg class="i"><use href="#i-film"/></svg>'}</span>
          <label class="agf"><span>${t('The post')}</span>${plVids().length ? `<select data-vp="${i}"${dis}><option value="">${t('Paste its link below, or pick it…')}</option>${plVids().map(p => `<option value="${esc(p.url)}"${p.url === v.link ? ' selected' : ''}>${esc(`${p.date || ''} · ${String(p.title || p.id).slice(0, 60)}`)}</option>`).join('')}</select>` : ''}
            <input type="url" data-vu="${i}" value="${esc(v.link || '')}" placeholder="${ta('Link to the post')}"${dis}></label>
          <label class="agf"><span>${t('Made in MotionLab')}</span><select data-vj="${i}"${dis}><option value="">${t('None')}</option>${vids.map(p => `<option value="${esc(p.name)}"${v.project === p.name ? ' selected' : ''}>${esc(pname(p))}</option>`).join('')}</select></label>
          ${v.numbers ? `<div class="exnums">${Object.keys(EX_METRIC()).map(k => `<span class="${k === T.rule.metric ? 'on' : ''}${v.numbers[k] == null ? ' none' : ''}" title="${esc(v.numbers[k] == null ? (EX_WHY()[(v.missing || {})[k]] || '') : EX_METRIC()[k])}"><b>${exVal(k, v.numbers[k])}</b>${esc(EX_METRIC()[k])}</span>`).join('')}</div>` : ''}
          ${v.spark ? `<a class="btn sm ghost" href="#/spark/${encodeURIComponent(v.spark.name)}" data-exgo><svg class="i"><use href="#i-sparkle"/></svg>SPARK</a>` : ''}</div>`).join('')
          + (!closed && T.versions.length < 3 ? `<button class="exadd" id="exadd"><svg class="i"><use href="#i-plus"/></svg>${t('Add a version C')}</button>` : '');
        $$('[data-vl]', m).forEach(x => x.oninput = () => { T.versions[+x.dataset.vl].label = x.value; });
        $$('[data-vu]', m).forEach(x => x.oninput = () => { T.versions[+x.dataset.vu].link = x.value.trim(); });
        $$('[data-vp]', m).forEach(x => x.onchange = () => { const i = +x.dataset.vp; T.versions[i].link = x.value;
          const p = pageVids.find(y => y.url === x.value); T.versions[i].thumb = p ? p.thumb : ''; vgrid(); });
        $$('[data-vj]', m).forEach(x => x.onchange = () => { T.versions[+x.dataset.vj].project = x.value; });
        $$('[data-vx]', m).forEach(x => x.onclick = () => { T.versions.splice(+x.dataset.vx, 1); vgrid(); });
        $$('[data-exgo]', m).forEach(x => x.onclick = () => closeModal());
        const add = $('#exadd', m);
        if (add) add.onclick = () => { T.versions.push({id: 'C', label: '', link: '', project: '', render: ''}); vgrid(); };
        const ser = T.versions.map(v => { const id = agVidId(T.platform, v.link), R = id && (SOC.retention || {})[`${T.platform}:${id}`];
          return R ? {id: v.id, points: R.points || [], end_s: R.end_s} : null; }).filter(Boolean);
        $('#excv', m).innerHTML = ser.length ? `<div class="excvw"><span class="small muted">${t('Where people left')}</span>${exCurves(ser)}
          <span class="exleg">${ser.map(s => `<i style="--vc: ${EXC[s.id]}"></i>${s.id}`).join(' ')}</span></div>` : '';
      };
      vgrid();
      $$('[data-xp]', m).forEach(b => b.onclick = () => { T.platform = b.dataset.xp; $$('[data-xp]', m).forEach(x => x.classList.toggle('on', x === b)); vgrid(); });
      // Claude's review, or what it needs first (every version posted and read by SPARK)
      const RV = T.review, posted = T.versions.every(v => v.link), unread = T.versions.filter(v => v.link && !v.spark);
      const winner = (T.decision && T.decision.pick !== 'none' && T.decision.pick) || (T.result || {}).winner;
      const base = T.versions.find(v => v.id === winner && v.project) || T.versions.find(v => v.project);
      $('#exrev', m).innerHTML = RV ? `<div class="panel exreview"><div class="sph"><h2><svg class="i"><use href="#i-claude"/></svg>${t("Claude's review")}</h2><span class="small dim">${esc(whenStr(RV.made) || RV.made)}</span></div>
          <p>${esc(RV.summary)}</p>
          ${T.versions.map(v => { const its = (RV.items || []).filter(x => x.version === v.id);
            return its.length ? `<div class="exrv" style="--vc: ${EXC[v.id]}"><b class="exvid">${v.id}</b><div class="exits">${its.map(x => `<div class="exitem ${x.kind}">
              <div class="exih"><span class="exk">${EX_KIND()[x.kind]}</span><span class="ntc">${esc(x.at_label)} – ${esc(x.end_label)}</span>${x.how ? `<span class="exhow">${EX_HOW()[x.how]}</span>` : ''}${x.to_test ? `<span class="extt" title="${ta('Not proven - the next test measures it')}">${t('to test')}${x.metric ? ' · ' + esc(EX_METRIC()[x.metric] || '') : ''}</span>` : ''}</div>
              <p>${esc(x.text)}</p>${x.quote ? `<div class="small muted">“${esc(x.quote.text)}”</div>` : ''}${x.retention && x.retention.to != null ? `<div class="small dim">${t('still watching: {a} → {b}', {a: rtPct(x.retention.from), b: rtPct(x.retention.to)})}</div>` : ''}</div>`).join('')}</div></div>` : ''; }).join('')}
          <div class="exnext"><b>${t('Next test')}</b> ${esc(RV.next_test.try)} <span class="muted">· ${t('the same: {what}', {what: esc(RV.next_test.same)})} · ${esc(EX_METRIC()[RV.next_test.metric] || '')}</span></div>
          <div class="row" style="margin-top:10px">${base ? claudeBtn(`/recreate-video improve ${base.project} test:${T.id}`, t('Make the next version'), 'recreate', base.project, 'cl') : `<span class="small muted">${t('Pick the MotionLab video a version was made in, and Claude can make the next version from this review.')}</span>`}
            ${closed ? '' : claudeBtn(`/spark test ${T.id}`, t('Review it again'), 'spark', T.id, 'sm ghost')}</div></div>`
        : isNew || !posted ? '' : unread.length ? `<div class="exneed"><span class="small muted">${t("Claude's review reads every version's words and shots first - SPARK reads them (no Claude).")}</span>
          <button class="btn" id="exspk"><svg class="i"><use href="#i-sparkle"/></svg>${tn(unread.length, 'Read {n} version with SPARK', 'Read {n} versions with SPARK')}</button></div>`
        : closed ? '' : `<div class="exneed"><span class="small muted">${t('Claude reads both versions and writes what to keep, change or cut in the next one - every change marked as something to test.')}</span>${claudeBtn(`/spark test ${T.id}`, t('Review it with Claude'), 'spark', T.id, 'cl')}</div>`;
      const spk = $('#exspk', m);
      if (spk) spk.onclick = async () => { spk.disabled = true;
        try { await api('/api/spark/batch', {links: unread.map(v => v.link), claude: false}); toast(t('SPARK is reading them - open the test again when they are ready'), 'ok'); }
        catch (e) { toast(e.message, 'err'); spk.disabled = false; } };
      // the actions: save / close / test again / delete
      const save = async () => {
        Object.assign(T, {title: $('#ext', m).value.trim(), change: $('#exc', m).value.trim(),
          rule: {metric: $('#exm', m).value, min_views: Math.max(0, parseInt($('#exmv', m).value, 10) || 0)}});
        try { const r = await api('/api/agency/tests', {action: 'save', test: T}); toast(t('Test saved'), 'ok'); reload(r.id); }
        catch (e) { toast(e.message, 'err'); }
      };
      const del = async () => { try { await api('/api/agency/tests', {action: 'delete', id: T.id}); closeModal(); reload(); } catch (e) { toast(e.message, 'err'); } };
      const D = T.decision;
      $('#exact', m).innerHTML = closed
        ? `<span class="small exdec">${D.pick === 'none' ? t('Closed - you went on with neither') : t('Closed - you went on with {v}', {v: esc(D.pick)})}${D.note ? ` · ${esc(D.note)}` : ''}</span><span class="grow"></span>
          <button class="btn pri" id="exagain"><svg class="i"><use href="#i-restart"/></svg>${t('Test again')}</button><button class="btn danger" id="exdel">${t('Delete')}</button>`
        : `<button class="btn pri" id="exok">${t('Save')}</button><button class="btn ghost" id="exno">${t('Cancel')}</button><span class="grow"></span>
          ${isNew ? '' : `<button class="btn" id="excl">${t('Close the test…')}</button><button class="btn danger" id="exdel">${t('Delete')}</button>`}`;
      const on = (id, fn) => { const b = $(id, m); if (b) b.onclick = fn; };
      on('#exok', save); on('#exno', closeModal); on('#exdel', del);
      on('#exagain', async () => { try { const r = await api('/api/agency/tests', {action: 'again', id: T.id}); toast(t('A new test, linked to this one'), 'ok'); reload(r.id); } catch (e) { toast(e.message, 'err'); } });
      on('#excl', () => {
        let pick = (T.result || {}).winner || '';
        const draw = () => { $('#exclose', m).innerHTML = `<div class="exclose"><b>${t('Which version do you go on with?')}</b>
            <span class="brpills">${[...T.versions.map(v => v.id), 'none'].map(x => `<button class="brpill${pick === x ? ' on' : ''}" data-pk="${x}">${x === 'none' ? t('Neither') : esc(x)}</button>`).join('')}</span>
            <input type="text" id="exnote" maxlength="500" placeholder="${ta('Why - in your words (optional)')}">
            <button class="btn pri" id="exclok"${pick ? '' : ' disabled'}>${t('Close the test')}</button>
            <div class="small muted">${t('A closed test stays as it is; Test again starts a new one from the version you keep.')}</div></div>`;
          $$('[data-pk]', m).forEach(b => b.onclick = () => { pick = b.dataset.pk; draw(); });
          on('#exclok', async () => { try { await api('/api/agency/tests', {action: 'close', id: T.id, pick, note: $('#exnote', m).value}); toast(t('Test closed'), 'ok'); reload(T.id); } catch (e) { toast(e.message, 'err'); } }); };
        draw();
      });
    }, 'wide exmodal');
  };
  drawTests();
  // ---- What works (R3): read when the tab is first opened; Test them again, Measure my posts, keep / forget
  const lbox = $('#aglearn', main);
  let LRN = null;
  const drawLearn = async fresh => {
    if (!LRN || fresh) {
      if (!LRN) lbox.innerHTML = `<div class="small muted" style="margin-top:16px">${t('Reading your posts…')}</div>`;
      try { LRN = await api('/api/agency/learn'); } catch (e) { lbox.innerHTML = `<div class="small bad" style="margin-top:16px">${esc(e.message)}</div>`; return; }
    }
    const L = LRN, need = 2 * L.min_side;
    const unread = pageVids.filter(v => v.url && ['tiktok', 'youtube', 'instagram'].includes(v.platform) && !(SOC.spark || {})[`${v.platform}:${v.id}`]);
    lbox.innerHTML = `<div class="exbar"><button class="btn" id="fdre"><svg class="i"><use href="#i-update"/></svg>${t('Test them again')}</button>
        ${unread.length ? `<button class="btn" id="fdspk" title="${ta('SPARK downloads each one and measures its first 3 seconds, its cuts and its words - no Claude. Ten at a time.')}"><svg class="i"><use href="#i-sparkle"/></svg>${t('Measure my posts with SPARK ({n} left)', {n: unread.length})}</button>` : ''}
        <span class="small muted">${t('Patterns across your own posts. Each one is a hunch until new posts confirm it - and a pattern never explains one video.')}</span></div>
      ${L.findings.length ? `<h2 class="nh">${t('Your lessons')} <span class="ncount">${L.findings.length}</span></h2><div class="fdgrid">${L.findings.map(fdCard).join('')}</div>` : ''}
      <h2 class="nh">${t('Patterns in your posts now')}</h2>
      ${L.candidates.length ? `<div class="small muted">${t('MotionLab tried {n} patterns - some will be chance. Keep one and your next posts test it.', {n: L.tried})}</div>
          <div class="fdgrid">${L.candidates.map((c, i) => `<div class="fdcard cand"><p class="fdclaim">${fdClaim(c)}</p>${fdNums(c.metric, c.run)}
            <div class="row"><span class="grow"></span><button class="btn sm" data-fdk="${i}">${t('Keep as a hunch')}</button></div></div>`).join('')}</div>`
        : `<div class="fdbars"><div class="small muted">${t('None stands out yet. A pattern needs {n} videos on each side - {all} posts with the same number.', {n: L.min_side, all: need})}</div>
          ${Object.entries(L.bars).map(([pl, b]) => `<div class="fdbar"><div class="fdbh">${brandPgLogo(pl)}<b>${esc(BRAND_PAGES[pl] || pl)}</b><span class="small muted">${tn(b.posts, '{n} post in the last 120 days', '{n} posts in the last 120 days')} · ${t('{n} measured by SPARK', {n: b.measured})}</span></div>
            <div class="fdmet">${L.metrics.map(m => `<span class="${b.metrics[m] >= need ? 'ok' : ''}"><i style="width:${Math.min(100, b.metrics[m] / need * 100).toFixed(0)}%"></i><b>${b.metrics[m]}</b> / ${need} · ${esc(EX_METRIC()[m])}</span>`).join('')}</div></div>`).join('')
            || `<div class="small muted">${t('No posts read yet - Your videos > Check my pages.')}</div>`}</div>`}`;
    const on = (sel, fn) => { const b = $(sel, lbox); if (b) b.onclick = fn; };
    on('#fdre', async () => { try { const r = await api('/api/agency/learn', {action: 'retest'}); const n = k => r.changes.filter(c => c.change === k).length;
      toast(r.changes.length ? t('Tested again: {c} confirmed, {w} weakened, {r} refuted', {c: n('confirmed'), w: n('weakened'), r: n('refuted')}) : t('No lessons kept yet'), 'ok'); drawLearn(true); }
      catch (e) { toast(e.message, 'err'); } });
    on('#fdspk', async () => { const b = $('#fdspk', lbox); b.disabled = true;
      try { await api('/api/spark/batch', {links: unread.slice(0, 10).map(v => v.url), claude: false}); toast(t('SPARK is measuring them - come back when they are ready'), 'ok'); }
      catch (e) { toast(e.message, 'err'); b.disabled = false; } });
    $$('[data-fdk]', lbox).forEach(b => b.onclick = async () => { const c = L.candidates[+b.dataset.fdk];
      try { await api('/api/agency/learn', {action: 'keep', spec: {platform: c.platform, feature: c.feature, metric: c.metric, direction: c.direction}}); toast(t('Kept as a hunch - your next posts test it'), 'ok'); drawLearn(true); }
      catch (e) { toast(e.message, 'err'); } });
    $$('[data-fdx]', lbox).forEach(b => b.onclick = async () => {
      try { await api('/api/agency/learn', {action: 'forget', id: b.dataset.fdx}); drawLearn(true); } catch (e) { toast(e.message, 'err'); } });
  };
  if (tab0 === 'learn') drawLearn();
  // ---- Monthly review (R4): a month at a time (‹ ›); the lab's numbers first, then last month's next tests and
  // Claude's three - Put it on the calendar = an idea (added to this page's calendar too, so its next save keeps it)
  const mbox = $('#agrev', main);
  let MON = null;
  const drawMonth = async (m, fresh) => {
    if (!MON || fresh || (m && m !== MON.month)) {
      if (!MON) mbox.innerHTML = `<div class="small muted" style="margin-top:16px">${t('Reading your posts…')}</div>`;
      try { MON = await api('/api/agency/month' + (m ? '?m=' + encodeURIComponent(m) : '')); }
      catch (e) { mbox.innerHTML = `<div class="small bad" style="margin-top:16px">${esc(e.message)}</div>`; return; }
    }
    const M = MON, R = M.review, posts = M.posts || [], byKey = Object.fromEntries(posts.map(p => [p.key, p]));
    const cmd = `/spark month ${M.month}`, lessonBy = Object.fromEntries((M.lessons || []).map(x => [x.id, x]));
    const picked = tr => (M.picked || []).find(x => x.try === tr && x.status !== 'removed');
    const ev = e => e.type === 'post' ? `<a class="mnev" href="${esc(e.url || '#')}" target="_blank" rel="noopener">${e.thumb ? `<img src="${fileUrl(e.thumb)}" alt="">` : '<svg class="i"><use href="#i-film"/></svg>'}<span>${esc(e.label)}</span></a>`
      : e.type === 'lesson' ? `<span class="mnev"><svg class="i"><use href="#i-target"/></svg><span>${lessonBy[e.id] ? fdClaim(lessonBy[e.id]) : esc(e.label)}</span></span>`
      : `<button class="mnev" data-mt="${esc(e.id)}"><svg class="i"><use href="#i-ab"/></svg><span>${esc(e.label)}</span></button>`;
    const plats = Object.entries(M.platforms || {});
    const before = (M.before || []).length ? `<h2 class="nh">${t('Last month’s next tests')}</h2><div class="mnrows">${M.before.map(x => `<div class="mnrow">${mnSt(x.status)}${brandPgLogo(x.platform)}
        <span class="grow">${esc(x.try)}</span><span class="small dim">${esc(EX_METRIC()[x.metric] || '')}</span>${Object.values(x.links || {}).map(u => `<a class="small" href="${esc(u)}" target="_blank" rel="noopener">${t('the post')}</a>`).join(' ')}</div>`).join('')}</div>` : '';
    mbox.innerHTML = `<div class="exbar mnbar"><button class="btn sm ghost icon" data-mm="${esc(M.prev)}" title="${ta('The month before')}">‹</button>
        <b class="mnmonth">${esc(mnMonth(M.month))}</b><button class="btn sm ghost icon" data-mm="${esc(M.next || '')}"${M.next ? '' : ' disabled'} title="${ta('The month after')}">›</button>
        <span class="small muted grow">${M.checked ? t('Numbers from your last Check my pages, {when}', {when: esc(whenStr(M.checked) || M.checked)}) : t('No posts read yet - Your videos > Check my pages.')}</span>
        ${posts.length && R ? claudeBtn(cmd, t('Write them again'), 'spark', 'month ' + M.month, 'sm ghost') : ''}</div>
      ${!posts.length ? `<div class="agvempty"><svg class="i"><use href="#i-month"/></svg><b>${t('No posts went up in {month}', {month: esc(mnMonth(M.month))})}</b>
        <span class="small muted">${t('Your posts come from Check my pages in Your videos.')}</span></div>${before}` : `
      <div class="mnplats">${plats.map(([pl, s]) => `<div class="mnplat"><div class="mnph">${brandPgLogo(pl)}<b>${esc(BRAND_PAGES[pl] || pl)}</b>
          <span class="small muted">${tn(s.posts, '{n} post', '{n} posts')}${s.young ? ' · ' + tn(s.young, '{n} still growing', '{n} still growing') : ''}</span></div>
          <div class="mnbig"><b class="mnx${mnXc(s.median_x)}">${mnX(s.median_x)}</b><span class="small muted">${s.usual_views != null
            ? t('the month’s median against your usual ({n} views)', {n: agNum(s.usual_views)}) : t('Your usual needs {n} posts at least a week old', {n: M.usual_min})}</span></div>
          ${s.traced ? `<div class="small"><b>${rtPct(s.median_hold_3s)}</b> ${t('still watching at 3 s')}${s.usual_hold_3s != null ? ` · ${t('usual {v}', {v: rtPct(s.usual_hold_3s)})}` : ''}</div>` : ''}</div>`).join('')}</div>
      ${M.top_views.length ? `<h2 class="nh">${t('Best by views')}</h2><div class="mnposts">${M.top_views.map(k => mnPost(byKey[k])).join('')}</div>` : ''}
      ${M.top_hold.length ? `<h2 class="nh">${t('Held best at 3 s')}</h2><div class="mnposts">${M.top_hold.map(k => mnPost(byKey[k], true)).join('')}</div>` : ''}
      ${(M.groups || []).length ? `<h2 class="nh">${t('What they had in common')}</h2><div class="small muted">${t('A month is a few posts - a hint, not a pattern. What works tests patterns over more posts.')}</div>
        <div class="mngrps">${mnGroups(M.groups)}</div>` : ''}
      ${(M.tests || []).length ? `<h2 class="nh">${t('Tests this month')}</h2><div class="mnrows">${M.tests.map(x => { const [sl, sc] = EX_STATE()[x.state] || ['', '--dim'];
        return `<button class="mnrow" data-mt="${esc(x.id)}"><span class="exst" style="--sc: var(${sc})">${sl}</span>${brandPgLogo(x.platform)}<span class="grow">${esc(x.title)}</span>${mnRes(x)}</button>`; }).join('')}</div>` : ''}
      ${(M.lessons || []).length ? `<h2 class="nh">${t('Your lessons')}</h2><div class="mnrows">${M.lessons.map(x => { const [sl, sc] = FD_ST()[x.status] || ['', '--dim'];
        return `<div class="mnrow"><span class="exst" style="--sc: var(${sc})">${sl}</span><span class="grow">${fdClaim(x)}</span>${x.runs.length ? `<span class="small dim">${t('this month: {what}', {what: fdRun(x.runs[x.runs.length - 1])})}</span>` : ''}</div>`; }).join('')}</div>` : ''}
      ${before}
      <div class="panel mnrev"><div class="sph"><h2><svg class="i"><use href="#i-claude"/></svg>${t('Three next tests')}</h2>${R ? `<span class="small dim">${esc(whenStr(R.made) || R.made)}</span>` : ''}</div>
        ${R ? `<p>${esc(R.summary)}</p><div class="mngrid">${R.next_tests.map(x => { const pk = picked(x.try);
          return `<div class="mncard"><div class="mnch"><span class="mnn">${x.n}</span>${brandPgLogo(x.platform)}<span class="grow"></span>${pk ? mnSt(pk.status) : ''}</div>
            <p class="mntry">${esc(x.try)}</p>
            <div class="mnkv"><span>${t('The same')}</span><span>${esc(x.same)}</span></div>
            <div class="mnkv"><span>${t('Decided by')}</span><b>${esc(EX_METRIC()[x.metric] || x.metric)}</b></div>
            <p class="small muted">${esc(x.why)}</p><div class="mnevs">${x.evidence.map(ev).join('')}</div>
            <div class="row"><span class="grow"></span>${pk ? `<span class="small ok">${t('On your calendar')}</span>`
              : `<button class="btn sm pri" data-mnplan="${x.n}"><svg class="i"><use href="#i-calendar"/></svg>${t('Put it on the calendar')}</button>`}</div></div>`; }).join('')}</div>`
        : `<div class="exneed"><span class="small muted">${t('Claude reads this month’s numbers and writes three next tests: what to try, what stays the same, and the number that decides it.')}</span>
          ${claudeBtn(cmd, t('Three next tests with Claude'), 'spark', 'month ' + M.month, 'cl')}</div>`}</div>`}`;
    $$('[data-mm]', mbox).forEach(b => b.onclick = () => { if (b.dataset.mm) drawMonth(b.dataset.mm); });
    $$('[data-mt]', mbox).forEach(b => b.onclick = () => { const x = (TS.tests || []).find(y => y.id === b.dataset.mt);
      showTab('tests'); history.replaceState(null, '', '#/agency/tests'); if (x) exModal(x); });
    $$('[data-mnplan]', mbox).forEach(b => b.onclick = async () => { b.disabled = true;
      try { const r = await api('/api/agency/month', {action: 'plan', month: M.month, n: +b.dataset.mnplan});
        CAL.posts.push(r.post); paint(); toast(t('On your calendar as an idea'), 'ok'); drawMonth(M.month, true); }
      catch (e) { toast(e.message, 'err'); b.disabled = false; } });
  };
  if (tab0 === 'month') drawMonth();
  if (!AG_CHECK) api('/api/jobs').then(list => { const j = (list || []).find(x => x.kind === 'agency_check' && ['running', 'queued'].includes(x.status));
    if (j) agCheckWatch(j.id); }).catch(() => {});
}
