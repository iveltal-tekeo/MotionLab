/* MotionLab app - js/jobs.js: Claude skills, Jobs, Storage, Downloads (yt-dlp), brandData.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ skills
// Settings > Claude skills: the project's Claude Code commands - what each does, how to type it, where the app runs it
async function pageSkills(main) {
  const S = await api('/api/skills');
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1><div class="sub">${t("Claude skills: the commands you can type in Claude Code for MotionLab. The app's {icon} buttons run them for you.", {icon: '<svg class="i"><use href="#i-claude"/></svg>'})}</div></div></div>${setTabs('#/skills')}
    <div class="skgrid">${S.map(k => `<div class="panel skill${k.dev ? ' dev' : ''}"><div class="row sp"><b class="mono skname">/${esc(k.name)}</b>${k.dev ? `<span class="tag">${t('for developers')}</span>` : ''}</div>
      <div class="skbrief">${esc(t(k.brief || ''))}</div>
      <div class="skuses">${k.uses.map(u => `<div class="skuse"><code>${esc(u)}</code><button class="btn sm ghost" data-copy="${esc(u)}" title="${ta('Copy it, then paste it into Claude Code')}">${t('Copy')}</button></div>`).join('')}</div>
      <div class="row sp skfoot">${k.where ? `<span class="small muted">${t('In the app: {where}', {where: esc(t(k.where))})}</span>` : '<span></span>'}${claudeBtn('/' + k.name, t('Open in Claude Code'), k.task, k.name)}</div></div>`).join('')
      || `<div class="empty">${t('No skills in this copy of MotionLab.')}</div>`}</div>`;
  $$('[data-copy]', main).forEach(b => b.onclick = () => copy(b.dataset.copy));
}

// ============================================================================================ jobs
async function pageJobs(main, id) {
  const list = await api('/api/jobs');
  // a job's status is its id (the tag's CSS class, compared below); the page shows its words (server-app's part, by key)
  main.innerHTML = `<div class="head"><div><h1>${t('Jobs')}</h1><div class="sub">${t('What MotionLab is working on. Jobs keep running when you switch pages.')}</div></div>
    <div class="row"><button class="btn" data-k="selftest">${t('Run the self-test')}</button><button class="btn" data-k="storage">${t('Storage report')}</button></div></div>
    <div class="grid" style="grid-template-columns:minmax(0,1fr) minmax(0,1.6fr)">
      <div class="panel"><table class="t click"><thead><tr><th>#</th><th>${t('Job')}</th><th>${t('Status')}</th><th class="num">${t('Time')}</th></tr></thead><tbody>
      ${list.map(j => `<tr data-id="${j.id}" class="${+id === j.id ? 'sel' : ''}"><td class="mono">${j.id}</td><td>${esc(j.title)}<div class="small dim">${esc(j.started)}</div></td>
        <td><span class="tag ${j.status}">${esc(t(j.status))}</span>${j.status === 'failed' ? `<div>${reportBtn(j.id, 'sm ghost')}</div>` : ''}</td><td class="num">${j.status === 'queued' ? '–' : j.seconds + 's'}</td></tr>`).join('') || `<tr><td colspan="4" class="muted">${t('No jobs yet in this session.')}</td></tr>`}
      </tbody></table></div>
      <div class="panel" id="jd">${id ? '' : `<div class="muted">${t('Select a job to see its output.')}</div>`}</div></div>`;
  $$('[data-k]', main).forEach(b => b.onclick = () => startJob(b.dataset.k, {}));
  $$('tr[data-id]', main).forEach(tr => tr.onclick = () => { location.hash = '#/jobs/' + tr.dataset.id; });
  if (!id) return;
  const j = list.find(x => x.id === +id);
  if (!j) { $('#jd').innerHTML = `<div class="muted">${t('This job is not in this session.')}</div>`; return; }
  $('#jd').innerHTML = `<div class="row sp"><h2>${esc(j.title)}</h2><span class="tag ${j.status}" id="jst">${esc(t(j.status))}</span></div>
    <div class="small muted mono" style="margin-bottom:8px">${esc(j.command)}</div>
    ${j.then_claude ? `<div class="small amber" style="margin-bottom:8px"><svg class="i"><use href="#i-claude"/></svg>${t('Claude Code opens by itself when this measuring is done.')}</div>` : ''}<pre class="log" id="jlog"></pre>
    <div class="row" style="margin-top:8px"><button class="btn danger" id="jc" ${['running', 'queued'].includes(j.status) ? '' : 'hidden'}>${j.status === 'queued' ? t('Remove from the queue') : t('Stop this job')}</button>
      <span id="jrep">${j.status === 'failed' ? reportBtn(j.id) : ''}</span></div>`;
  $('#jc').onclick = async () => { if (!confirm(t('{action}?', {action: $('#jc').textContent}))) return; try { await api(`/api/jobs/${id}/cancel`, {}); } catch (e) { toast(e.message, 'err'); } };
  const shown = s => s === 'queued' ? t('waiting its turn') : t(s || '');
  followJob(+id, $('#jlog'), jj => {
    $('#jst').className = 'tag ' + jj.status; $('#jst').textContent = shown(jj.status); $('#jc').hidden = true;
    if (jj.status === 'failed') $('#jrep').innerHTML = reportBtn(jj.id);
    toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
  }, jj => {
    $('#jst').className = 'tag ' + jj.status; $('#jst').textContent = shown(jj.status);
    $('#jc').textContent = jj.status === 'queued' ? t('Remove from the queue') : t('Stop this job');
    $('#jc').hidden = !['running', 'queued'].includes(jj.status);
  });
}

// ============================================================================================ storage
// Settings' tabs: General (#/settings), Storage (#/storage, 0.3.3) and Claude skills (#/skills, a tab since 0.4)
const setTabs = cur => `<div class="tabs">${[['#/settings', t('General')], ['#/storage', t('Storage')], ['#/skills', t('Claude skills')]].map(([h, l]) =>
  `<a href="${h}" class="${h === cur ? 'on' : ''}">${l}</a>`).join('')}</div>`;
async function pageStorage(main) {
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1></div></div>${setTabs('#/storage')}<div class="loading">${t('Measuring every folder of the lab… (a few seconds)')}</div>`;
  const S = await api('/api/storage');
  const COL = {source: '#4fb3ff', keep: '#3ecf8e', cache: '#ffc400', checks: '#ff9f43', finals: '#c56bff', env: '#5c5c66'};
  // the categories' names as storage.py says them (--what cache,checks,finals); shown in the app's language
  const CAT = {source: t('source|storage'), keep: t('keep|storage'), cache: t('cache|storage'), checks: t('checks|storage'),
               finals: t('finals|storage'), env: t('env|storage')};
  const used = S.units.reduce((a, u) => a + u.total, 0);
  const target = u => u === 'tools\\selftest' ? 'selftest' : u.split('\\').pop();
  main.innerHTML = `<div class="head"><div><h1>${t('Settings')}</h1><div class="sub">${t('Storage: MotionLab uses {used} · {free} free of {total} on this drive. Only data the lab can rebuild can be freed; your videos and everything learned are never touched.', {used: bytes(used), free: bytes(S.free_bytes), total: bytes(S.total_bytes)})}</div></div></div>${setTabs('#/storage')}
    <div class="row small" style="margin-bottom:10px">${S.cats.map(c => `<span class="chip"><i class="sw" style="background:${COL[c]}"></i>${CAT[c] || c}</span>`).join('')}
      <span class="hint">${t('source = your videos · keep = results and knowledge · cache = rebuildable · checks = comparison videos · finals = full renders')}</span></div>
    <div class="panel"><table class="t"><thead><tr><th>${t('Folder')}</th><th></th>${S.cats.map(c => `<th class="num">${CAT[c] || c}</th>`).join('')}<th class="num">${t('total')}</th><th></th></tr></thead><tbody>
    ${S.units.map(u => { const fr = S.prunable.reduce((a, c) => a + u[c], 0); return `<tr><td class="mono small">${esc(u.name)}</td>
      <td><div class="stbar">${S.cats.map(c => `<i style="width:${100 * u[c] / Math.max(1, u.total)}%;background:${COL[c]}"></i>`).join('')}</div></td>
      ${S.cats.map(c => `<td class="num small">${u[c] ? bytes(u[c]) : '–'}</td>`).join('')}<td class="num">${bytes(u.total)}</td>
      <td>${fr > 5e6 && u.name !== '.venv' ? `<button class="btn sm" data-t="${esc(target(u.name))}" data-n="${esc(u.name)}">${t('Free space…')}</button>` : ''}</td></tr>`; }).join('')}
    </tbody></table></div>
    <h3>${t('What can be freed, and how it comes back')}</h3><div class="panel"><table class="t"><tbody>
    ${S.freeable.map(f => `<tr><td class="num" style="width:90px">${bytes(f.bytes)}</td><td><b>${esc(t(f.what))}</b></td><td class="small muted">${esc(t(f.how))}</td></tr>`).join('')}</tbody></table></div>`;
  $$('[data-t]', main).forEach(b => b.onclick = () => modal(`<h2>${t('Free space: {name}', {name: esc(b.dataset.n)})}</h2>
    <p class="hint">${t('Pick what may go. First a dry run lists every file; nothing is deleted until you confirm.')}</p>
    <div class="col"><label class="chk"><input type="checkbox" value="cache" checked> ${t('cache (rebuildable data, e.g. footage caches)')}</label>
      <label class="chk"><input type="checkbox" value="checks"> ${t('checks (comparison videos, section renders)')}</label>
      <label class="chk"><input type="checkbox" value="finals"> ${t('finals (full renders)')}</label></div>
    <div class="row" style="margin-top:12px"><button class="btn" id="dry">${t('Dry run')}</button><button class="btn danger" id="real" disabled>${t('Delete these files')}</button></div>
    <pre class="log" id="plog" style="margin-top:10px" hidden></pre>`, el => {
    const what = () => $$('input[type=checkbox]:checked', el).map(x => x.value);
    $('#dry', el).onclick = async () => {
      const j = await startJob('prune', {target: b.dataset.t, what: what(), yes: false}, false); if (!j) return;
      const pre = $('#plog', el); pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, jj => { $('#real', el).disabled = jj.status !== 'done'; });
    };
    $('#real', el).onclick = async () => {
      if (!confirm(t('Delete the files listed in the dry run? They can be rebuilt, but that takes time.'))) return;
      const j = await startJob('prune', {target: b.dataset.t, what: what(), yes: true}, false); if (!j) return;
      const pre = $('#plog', el); pre.textContent = ''; $('#real', el).disabled = true;
      followJob(j.id, pre, jj => toast(t('Free space: {status}', {status: t(jj.status)}), jj.status === 'done' ? 'ok' : 'err'));
    };
  }));
}

// ============================================================================================ downloads (yt-dlp)
const FILE_RX = /^[A-Za-z]:\\.+\.(mp4|mkv|webm|mov|m4v|mp3|m4a)$/i;
// Settings > Programs: the pinned HyperFrames / GSAP vs the newest on npm (asked once a day, motionlab.upstream) and
// the upgrade test (overlay.py upgrade-test renders the examples with both versions and compares every frame)
function upstreamBox(S) {
  const U = S.upstream || {}, P = U.packages || {}, hf = P.hyperframes || {}, gs = P.gsap || {};
  if (!hf.pinned || !(S.tools.find(x => x.name === 'hyperframes') || {}).found) return '';
  const pkg = (name, p) => `${name} <b>${esc(p.pinned)}</b>${p.installed && p.installed !== p.pinned ? ` <span class="amber">${t('(installed {version} - Install again)', {version: esc(p.installed)})}</span>` : ''}${p.latest ? (p.newer
    ? ` · <span class="amber">${t('{version} on npm', {version: esc(p.latest)})}</span> <a href="${esc(p.notes)}" target="_blank" rel="noopener">${t('what changed')}</a>` : ' · ' + t('the newest')) : ''}`;
  const tst = hf.latest && (U.tests || {})[hf.latest];
  const worst = tst && tst.examples ? Math.max(...tst.examples.map(x => x.max_diff ?? 255)) : null;
  // the first message for Claude stays English (Claude commands are never translated)
  const adopt = tst && tst.pass ? `Pin HyperFrames ${tst.hyperframes}${tst.gsap !== gs.pinned ? ` and GSAP ${tst.gsap}` : ''} for MotionLab: run tools\\overlay.py pin ${tst.hyperframes}${tst.gsap !== gs.pinned ? ` --gsap ${tst.gsap}` : ''}, then selftest.py --extended and tools\\dev\\smoke.py, and add a CHANGELOG line` : '';
  const day = tst ? esc(String(tst.when || '').slice(0, 10)) : '';
  const test = !hf.newer && !gs.newer ? '' : tst ? (tst.pass
      ? `<span class="tag done">${t('tested {day}: same frames', {day})}</span> <span class="small muted">${tn(tst.examples.length, '(max {worst}/255 on {n} examples, render {times}). A MotionLab update brings it once the repo owner adopts it.', '(max {worst}/255 on {n} examples, render {times}). A MotionLab update brings it once the repo owner adopts it.', {worst, times: tst.examples.map(x => `${numStr(x.seconds_pinned)} → ${numStr(x.seconds_candidate)} s`).join(', ')})}</span> ${claudeBtn(adopt, t('Adopt it (repo owner)'), 'free', 'hyperframes')}`
      : `<span class="tag failed">${t('tested {day}: frames differ', {day})}</span> <span class="small muted">${t('{list} - MotionLab keeps {version}.', {list: tst.examples.map(x => `${esc(x.example)} ${x.error ? t('error') : x.max_diff + '/255'}`).join(' · '), version: esc(hf.pinned)})}</span>`)
      + ` <button class="btn sm" data-hftest>${t('Test again')}</button>`
    : `<button class="btn sm" data-hftest title="${ta('Installs it in a scratch folder (.app\\dev), renders the overlay examples with both versions and compares every frame - a few minutes, ~300 MB')}">${t('Test it')}</button>`;
  return `<div class="upstream small"><div><b>${t('HTML overlay packages:')}</b> ${pkg('HyperFrames', hf)} &nbsp;|&nbsp; ${pkg('GSAP', gs)}</div>
    <div class="row" style="margin-top:6px">${test}<span class="grow"></span><span class="dim">${U.checked ? t('npm checked {when}', {when: esc(U.checked.replace('T', ' ').slice(0, 16))}) : t('not checked yet')}${U.error ? ` · <span class="bad">${esc(U.error)}</span>` : ''}
      · <a href="#" id="upnpm">${t('check now')}</a></span></div>
    <div class="dim">${t('MotionLab only uses versions that passed this test; newer HyperFrames come several times a day.')}</div></div>`;
}
async function downloadModal() {
  const S = await api('/api/settings');
  const yt = S.tools.find(x => x.name === 'yt-dlp') || {};
  modal(`<h2>${t('Download from a link')}</h2>
    <p class="hint">${yt.found ? '' : `<b class="bad">${t('The downloader (yt-dlp) was not found.')}</b> ${esc(t(yt.how || ''))} · <a href="#/settings">${t('Settings')}</a><br>`}
      ${t('One video per link. Only download what you are allowed to use.')}</p>
    <input type="text" id="durl" placeholder="${ta('Paste a link - YouTube, TikTok, Instagram, Vimeo…')}">
    <div class="row" style="margin-top:10px"><select id="dpre">${S.presets.map(o => `<option value="${o.id}" ${o.id === S.settings.download_preset ? 'selected' : ''}>${esc(t(o.label))}</option>`).join('')}</select>
      <button class="btn pri" id="dgo" ${yt.found ? '' : 'disabled'}><svg class="i"><use href="#i-download"/></svg>${t('Download')}</button>
      <span id="dst" class="small muted"></span></div>
    <pre class="log" id="dlog" hidden style="max-height:240px;margin-top:10px"></pre>
    <div id="ddone" hidden style="margin-top:10px"></div>`, el => {
    const inp = $('#durl', el); inp.focus();
    inp.onkeydown = e => { if (e.key === 'Enter') $('#dgo', el).click(); };
    $('#dgo', el).onclick = async () => {
      const url = inp.value.trim();
      if (!/^https?:\/\//i.test(url)) { toast(t('Paste a full link starting with https://'), 'err'); return; }
      const j = await startJob('download', {url, preset: $('#dpre', el).value}, false);
      if (!j) return;
      $('#dgo', el).disabled = true; $('#dst', el).textContent = t('downloading…'); $('#ddone', el).hidden = true;
      const pre = $('#dlog', el); pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, done => {
        $('#dgo', el).disabled = false;
        $('#dst', el).innerHTML = done.status === 'done' ? t('done ✓') : esc(t(done.status)) + (done.status === 'failed' ? ' ' + reportBtn(done.id, 'sm ghost') : '');
        const file = pre.textContent.split('\n').map(l => l.trim()).reverse().find(l => FILE_RX.test(l));
        if (done.status !== 'done' || !file) return;
        const isVideo = !/\.(mp3|m4a)$/i.test(file);
        const rel = file.toLowerCase().startsWith(S.lab.toLowerCase() + '\\') ? file.slice(S.lab.length + 1).replace(/\\/g, '/') : '';
        const box = $('#ddone', el); box.hidden = false;
        box.innerHTML = `<div class="small">${t('Saved: {file}', {file: `<span class="mono">${esc(file)}</span>`})}</div>
          <div class="row" style="margin-top:8px">${isVideo ? `<button class="btn pri" id="dan">${t('Analyse it')}</button>` : ''}
          ${rel ? `<button class="btn" id="dop">${t('Show in folder')}</button>` : ''}</div>`;
        if (isVideo) $('#dan', el).onclick = () => { closeModal(); addVideosModal({files: [file], pick: true}); };
        if (rel) $('#dop', el).onclick = () => openPath(rel, true);
      });
    };
  });
}

// ---- "For my brand" (0.6.0; the user, 2026-10-25: "add an option when u generate or edit a video or create in
// general that is called 'its for my brand' and then gets the knowdledge and tailors the video to your brand, using
// icons colors url"): a switch (`<div class="brandrow">` in a dialog - modal() draws it) in New edit, the Generator
// and Prepare's three dialogs. Ticked, the request carries My Brand as it is now (the server copies it in, only the
// products switched on) and the brief tells Claude to use its colours, logo, website, voice and goal. Greyed out
// while My Brand is empty; the last choice is remembered on this PC.
let BRAND_DATA = null;                                  // My Brand as last read (null = read it again)
async function brandData() {
  if (BRAND_DATA === null) { try { BRAND_DATA = await api('/api/brand'); } catch (e) { BRAND_DATA = {}; } }
  return BRAND_DATA;
}
// the user's logo large and faint in My Brand's band, the shop icon stays (2026-10-25, the user: "what if u put the
// logo in teh transparent background in the My brand page instead of replacing the shop icon itself?")
function brandLogoSrc(lg, v) { return lg ? `/files/${lg.split('/').map(encodeURIComponent).join('/')}?v=${encodeURIComponent(v || '')}` : ''; }
// My Brand's colours as a palette (New edit, step 3): the accent first (a palette's first colour = its main accent),
// then neutral, text, background, then the ones without a job - upper case, n at most
function brandPalette(b, n = 6) {
  const cols = ((b || {}).identity || {}).colours || [], rank = {accent: 0, neutral: 1, text: 2, background: 3};
  return [...cols].sort((p, q) => (rank[p.role] ?? 4) - (rank[q.role] ?? 4)).map(c => String(c.hex).toUpperCase()).slice(0, n);
}
function brandBand(main, b) {
  const head = $('.head', main), src = brandLogoSrc(((b || {}).identity || {}).logo, (b || {}).updated);
  let bg = $('.brbg', head);
  if (!src) { if (bg) bg.remove(); return; }
  if (!bg) { bg = document.createElement('span'); bg.className = 'brbg'; bg.setAttribute('aria-hidden', 'true'); head.append(bg); }   // last: the title stays div:first-child
  bg.style.backgroundImage = `url("${src}")`;
}
const brandFilled = b => { const g = b.goal || {}, i = b.identity || {};     // = brand.filled
  return !!(b.name || b.about || (g.picks || []).length || g.words || (b.audience || []).length || (i.colours || []).length
            || i.voice || i.logo || Object.values(i.fonts || {}).some(Boolean) || (b.site || {}).url || (b.pages || []).length
            || (b.catalogue || []).length); };
// the switch + a small preview of what it gives Claude (2026-10-25, the user: "a small preview of what data its feeding?
// like url, logos what colors"): the logo, the colours, the website, the goal, the products switched on, the voice
function brandToggle(box) {
  box.innerHTML = `<label class="neres brandtg"><input type="checkbox" disabled><svg class="i"><use href="#i-brand"/></svg>
    <span><b>${t('For my brand')}</b><span class="brprev">${t('your colours, logo, website and voice - from My Brand')}</span></span></label>`;
  const cb = $('input', box), pv = $('.brprev', box);
  brandData().then(b => {
    const ok = brandFilled(b);
    let last = false;
    try { last = localStorage.getItem('ml.forBrand') === '1'; } catch (e) { /* storage blocked */ }
    cb.disabled = !ok; cb.checked = ok && last;
    if (!ok) { $('label', box).title = t('Fill in My Brand first (the sidebar, at the top)'); pv.textContent = t('My Brand is empty - fill it in first'); return; }
    const i = b.identity || {}, prods = (b.catalogue || []).filter(p => p.use !== false);
    const host = ((b.site || {}).url || '').replace(/^https?:\/\//, '').replace(/\/$/, '');
    const goal = ((b.goal || {}).picks || []).map(g => t((BRAND_GOALS.find(x => x[0] === g) || [g, g])[1]));
    pv.innerHTML = [i.logo ? `<img class="brpl" src="/files/${i.logo.split('/').map(encodeURIComponent).join('/')}" alt="">` : '',
      (i.colours || []).length ? `<span class="brpds">${i.colours.map(c => `<i style="background: ${esc(c.hex)}" title="${esc(c.name || c.hex)}"></i>`).join('')}</span>` : '',
      host ? `<span>${esc(host)}</span>` : '', goal.length ? `<span>${esc(goal.join(', '))}</span>` : '',
      prods.length ? `<span>${tn(prods.length, '{n} product', '{n} products')}</span>` : '',
      i.voice ? `<span>“${esc(i.voice)}”</span>` : ''].filter(Boolean).join('');
    $('label', box).title = t('Ticked, Claude gets this from My Brand and makes the video yours');
  });
  cb.onchange = () => { try { localStorage.setItem('ml.forBrand', cb.checked ? '1' : '0'); } catch (e) { /* storage blocked */ } };
}
const brandOn = (el, sel) => { const c = $(`${sel} input`, el); return !!(c && c.checked && !c.disabled); };
