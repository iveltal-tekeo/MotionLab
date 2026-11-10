/* MotionLab app - js/motion.js: Motion Graphics (#/motion): sounds, music, logos, clips; the prompt library page (#/prompts).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ Motion Graphics (0.5.0)
// the user (2026-10-16): "turn the Swishy reference clips (in the refs folder) I captured into a reusable Motion
// Graphics library, add a Motion Graphics section to the sidebar, and make Generate use those templates as well when
// generating blindly". GET /api/motion = data.motion(): the library = MotionLab's own HyperFrames templates
// (tools\overlays\motion\<id>: settings, picture, the clips each was learned from) + the packs of captured clips
// (analysis\templates\<pack>: measured with no Claude, Claude's cards). A template goes into a video like any graphic
// (job overlay_new, sized like the video's edit) or into the Generator (generate_request.json "templates").
const MKIND = {text: t('Text'), numbers: t('Numbers'), charts: t('Charts'), lists: t('Lists'), ui: t('Buttons & UI'), chat: t('Chat'),
  social: t('Social'), music: t('Music'), logo: t('Logo'), photos: t('Photos'), places: t('Places'), background: t('Backgrounds'), transitions: t('Transitions'),
  lower_thirds: t('Lower thirds'), callouts: t('Call-outs'), broadcast: t('News & broadcast'), promo: t('Promo & sale')};
const mkind = k => MKIND[k] || k;
const MSTATUS = [['', t('All|clips')], ['built', t('Rebuilt')], ['p1', t('Next to rebuild')], ['p2', t('Later')], ['p3', t('Style only')]];
const mclipStatus = it => it.built.length ? 'built' : it.still ? 'still' : 'p' + ((it.card || {}).rebuild || 2);
const MSTATUS_WORD = {built: t('rebuilt'), still: t('a still capture'), p1: t('next to rebuild'), p2: t('later'), p3: t('style only')};
const mdefaults = t => { const v = {}; (t.settings || []).forEach(s => { v[s.id] = s.default; }); return v; };
async function pageMotion(main, tab, open) {
  const [M, LGD, SD, MUS] = await Promise.all([api('/api/motion'), logoLoad().catch(() => ({logos: [], groups: {}})),
    api('/api/sounds').catch(() => ({sounds: [], packs: [], kinds: []})),
    api('/api/music').catch(() => ({tracks: [], unmeasured: 0, beds: [], make: {}, elevenlabs: {}}))]);
  tab = ['learned', 'logos', 'sounds', 'music'].includes(tab) ? tab : 'templates';
  const L = M.library, clips = M.packs.flatMap(p => p.items.map(it => ({...it, pack: p.pack})));
  const todo = clips.filter(it => mclipStatus(it) === 'p1' || mclipStatus(it) === 'p2');   // the skill does 1s first
  main.innerHTML = `<div class="head"><div><h1>${t('Motion Graphics')}</h1><div class="sub">${t('Designed motion to reuse - learned from pro template clips, or made for what creators use most, as MotionLab\'s own graphics. Change the words and colours, put one in a video, or let the Generator build a video from them.')}</div></div>
      ${todo.length && M.packs.length ? `<div class="row">${claudeBtn(`/generate-video templates ${M.packs[0].pack}`, tn(Math.min(todo.length, 8), 'Rebuild the next {n} with Claude', 'Rebuild the next {n} with Claude'), 'generate', 'templates', 'cl')}</div>` : ''}</div>
    <div class="tabs"><a href="#/motion" class="${tab === 'templates' ? 'on' : ''}">${t('Templates')} <span class="dim">${L.length}</span></a>
      <a href="#/motion/learned" class="${tab === 'learned' ? 'on' : ''}">${t('Learned from')} <span class="dim">${clips.length}</span></a>
      <a href="#/motion/logos" class="${tab === 'logos' ? 'on' : ''}">${t('Logos')} <span class="dim">${LGD.logos.length}</span></a>
      <a href="#/motion/sounds" class="${tab === 'sounds' ? 'on' : ''}">${t('Sounds')} <span class="dim">${SD.sounds.length}</span></a>
      <a href="#/motion/music" class="${tab === 'music' ? 'on' : ''}">${t('Music')} <span class="dim">${MUS.tracks.filter(x => !x.off).length}</span></a></div>
    <div id="mgbody"></div>`;
  const body = $('#mgbody', main);
  if (tab === 'templates') motionTemplates(body, M, L, clips);
  else if (tab === 'logos') motionLogos(body, M, LGD);
  else if (tab === 'sounds') motionSounds(body, SD);
  else if (tab === 'music') motionMusic(body, MUS);
  else motionClips(body, M, clips);
  if (open) { const tp = L.find(x => x.id === open); if (tp) motionModal(tp, M); }
}
function motionTemplates(body, M, L, clips) {
  if (!L.length) {
    body.innerHTML = emptyHero('motion', t('No templates yet'), t('Templates are rebuilt from the clips under “Learned from” - Claude rebuilds them in batches.'), '');
    return;
  }
  let kf = '';
  try { kf = localStorage.getItem('ml.mkind') || ''; } catch (e) { /* all */ }
  const draw = () => {
    const ks = [...new Set(L.map(tp => tp.kind))];
    if (kf && !ks.includes(kf)) kf = '';
    body.innerHTML = `<div class="hint" style="margin-bottom:10px">${t('Click one to play it and try your own words. Most were learned from the clips they name - their timing, eases and layout measured; the MotionLab originals fill the kinds template sites offer most (lower thirds, transitions, call-outs...). All are MotionLab\'s own graphics: free to use in any video.')}</div>
      <div class="row pfilters">${[['', t('All|templates')], ...ks.map(k => [k, mkind(k)])].map(([k, l]) => `<button class="fchip${k === kf ? ' on' : ''}" data-k="${esc(k)}">${esc(l)} <span class="dim">${k ? L.filter(tp => tp.kind === k).length : L.length}</span></button>`).join('')}</div>
      <div class="mggrid">${L.filter(tp => !kf || tp.kind === kf).map(tp => `<div class="mgc" data-id="${esc(tp.id)}" tabindex="0">${newTag(`m:${tp.id}@${Math.round(tp.created || 0)}`, tp.created)}
        <div class="mgpic">${tp.thumb ? `<img src="${fileUrl(tp.thumb)}?v=${tp.thumb_v}" alt="" loading="lazy">` : `<span class="dim small">${t('no picture yet')}</span>`}</div>
        <div class="row sp" style="margin-top:8px"><b>${esc(t(tp.name))}</b><span class="chip">${esc(mkind(tp.kind))}</span></div>
        <div class="small muted mgwhat">${esc(t(tp.what || ''))}</div>
        <div class="small dim">${dec(tp.frames / tp.fps, 1)} s · ${(tp.sources || []).length ? tn(tp.sources.length, 'learned from {n} clip', 'learned from {n} clips') : t('MotionLab original')}</div></div>`).join('')}</div>`;
    $$('[data-k]', body).forEach(b => b.onclick = () => { kf = b.dataset.k; try { localStorage.setItem('ml.mkind', kf); } catch (e) { /* not kept */ } draw(); });
    $$('.mgc', body).forEach(c => c.onclick = c.onkeydown = e => { if (e.type === 'keydown' && e.key !== 'Enter') return; motionModal(L.find(tp => tp.id === c.dataset.id), M); });
  };
  draw();
}
// Motion Graphics > Sounds (0.6.0 step 9; the user: "could it be possible for the user itself to choose them"): every
// recorded sound of this PC's library - ▶, its kind, where it came from and its licence; ★ = a favourite (a kind with
// any uses only them), the eye = hidden (never used, the file stays); *Add sounds* = a pack, a folder or a few files
// (the shared list sorts the packs MotionLab knows; the rest get their kind from their name, with where they came from)
let SD_FILTER = 'all', SD_KIND = '', SD_Q = '';
function motionSounds(body, SD) {
  let player = null;
  const hear = file => { try { if (player) player.pause(); player = new Audio(edSoundUrl(file)); player.play().catch(() => {}); } catch (e) { /* no sound */ } };
  const draw = () => {
    const q = SD_Q.toLowerCase();
    const wk = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10), isNew = s => (s.added || '') >= wk;
    const L = SD.sounds.filter(s => (SD_FILTER === 'all' ? !s.off : SD_FILTER === 'fav' ? s.fav && !s.off : SD_FILTER === 'new' ? isNew(s) : s.off)
      && (!SD_KIND || s.kind === SD_KIND) && (!q || `${s.name} ${s.kind} ${edKind(s.kind)} ${s.source}`.toLowerCase().includes(q)));
    const kinds = [...new Set(SD.sounds.map(s => s.kind))].sort((a, b) => edKind(a).localeCompare(edKind(b)));
    const groups = kinds.filter(k => L.some(s => s.kind === k));
    const n = f => SD.sounds.filter(f).length;
    const shareable = SD.sounds.some(s => s.made && /paid plan/.test(s.licence));
    body.innerHTML = `<div class="row sdtop"><button class="btn pri" id="sdmake"><svg class="i"><use href="#i-sparkle"/></svg>${t('Make sounds')}</button>
        <button class="btn" id="sdadd"><svg class="i"><use href="#i-upload"/></svg>${t('Add sounds')}</button>
        ${shareable ? `<button class="btn" id="sdshare" title="${ta('The sounds you made on a paid ElevenLabs plan as one file to put on Google Drive')}"><svg class="i"><use href="#i-shared"/></svg>${t('Share with friends')}</button>` : ''}
        <input type="search" id="sdq" placeholder="${ta('Search…')}" value="${esc(SD_Q)}">
        <select id="sdkind"><option value="">${t('All kinds')}</option>${kinds.map(k => `<option value="${esc(k)}"${k === SD_KIND ? ' selected' : ''}>${esc(edKind(k))}</option>`).join('')}</select>
        <span class="row pfilters">${[['all', t('In use'), n(s => !s.off)], ['new', t('New'), n(isNew)], ['fav', `★ ${t('Favourites')}`, n(s => s.fav && !s.off)], ['off', t('Hidden'), n(s => s.off)]].filter(([k, , c]) => k !== 'new' || c).map(([k, l, c]) =>
          `<button class="fchip${SD_FILTER === k ? ' on' : ''}" data-f="${k}">${l} <span class="dim">${c}</span></button>`).join('')}</span></div>
      ${SD.packs.length ? `<div class="sdpacks">${SD.packs.map(p => `<div class="sdpack"><div class="row sp"><b>${esc(p.name)}</b><span class="chip${p.here >= p.listed ? ' ok' : ''}">${t('{here} of {n} here', {here: p.here, n: p.listed})}</span></div>
          <div class="small muted">${esc(t(p.how || ''))}</div>
          <div class="row sp"><span class="small dim sdlic" title="${esc(p.licence || '')}">${esc(p.licence || '')}</span>${p.page ? `<a class="btn sm" href="${esc(p.page)}" target="_blank" rel="noopener">${t('Get it')}</a>` : p.here < p.listed ? `<span class="small dim">${t('Ask whoever shared MotionLab with you for its link')}</span>` : ''}</div></div>`).join('')}</div>` : ''}
      ${!SD.sounds.length ? emptyHero('music', t('No recorded sounds yet'), t('Videos get made-up sound effects until you add some. Add a pack you downloaded - MotionLab sorts the ones it knows.'), '')
        : !L.length ? `<div class="small muted">${t('Nothing matches.')}</div>`
        : groups.map(k => `<div class="sdgroup"><h3 class="row"><span class="eddot" style="--h:${meHue(k)}"></span>${esc(edKind(k))} <span class="dim">${L.filter(s => s.kind === k).length}</span></h3>
          ${L.filter(s => s.kind === k).map(s => `<div class="sdrow${s.off ? ' off' : ''}" data-file="${esc(s.file)}">
            <button class="btn sm ghost" data-hear title="${ta('Listen')}">▶</button><span class="grow sdname">${esc(s.name)}</span>
            ${s.made ? `<span class="chip sdel${/free plan/.test(s.licence) ? ' test' : ''}" title="${esc(s.licence)}">${/free plan/.test(s.licence) ? t('ElevenLabs · non-commercial') : 'ElevenLabs'}</span>` : ''}
            <span class="small dim">${s.len_s ? dec(s.len_s) + ' s' : ''}</span>${s.made ? '' : `<span class="small muted sdsrc" title="${esc(s.licence)}">${esc(s.source)}</span>`}
            <button class="btn sm ghost sdstar${s.fav ? ' on' : ''}" data-fav aria-pressed="${s.fav}" title="${ta('Favourite: its kind uses your favourites first')}">${s.fav ? '★' : '☆'}</button>
            <button class="btn sm ghost" data-off aria-pressed="${s.off}" title="${s.off ? ta('Use it again') : ta('Hide it: never used (the file stays)')}">${s.off ? t('Show') : t('Hide')}</button></div>`).join('')}</div>`).join('')}`;
    $('#sdadd', body).onclick = () => soundsAddModal(() => route(true));
    $('#sdmake', body).onclick = () => soundsMakeModal(SD, () => { SD_FILTER = 'new'; route(true); });
    if ($('#sdshare', body)) $('#sdshare', body).onclick = async () => { try { const r = await api('/api/sounds/share', {});
      toast(t('{n} sounds in {file} - put it on Google Drive (anyone with the link) and send your friends the link', {n: r.count, file: r.name}), 'ok'); } catch (e) { toast(e.message, 'err'); } };
    const qi = $('#sdq', body);
    qi.oninput = debounce(() => { SD_Q = qi.value; const pos = qi.selectionStart; draw(); const x = $('#sdq', body); x.focus(); x.setSelectionRange(pos, pos); }, 200);
    $('#sdkind', body).onchange = e => { SD_KIND = e.target.value; draw(); };
    $$('[data-f]', body).forEach(b => b.onclick = () => { SD_FILTER = b.dataset.f; draw(); });
    $$('.sdrow', body).forEach(r => {
      const s = SD.sounds.find(x => x.file === r.dataset.file);
      $('[data-hear]', r).onclick = () => hear(s.file);
      const set = async (k, v) => { try { await api('/api/sounds/set', {file: s.file, [k]: v}); s[k] = v; draw(); } catch (e) { toast(e.message, 'err'); } };
      $('[data-fav]', r).onclick = () => set('fav', !s.fav);
      $('[data-off]', r).onclick = () => set('off', !s.off);
    });
  };
  draw();
  onCleanup(() => { if (player) player.pause(); });
}
// Motion Graphics > Music (0.6.0 step 10; the user: a music library from the songs I download): the songs downloaded in
// the Analyser and the ones added, each measured once (tempo, energy, tone, length - New edit shows the same), and
// ambience beds for under a talking video. ▶ plays it here (one at a time, stopped when the page or a dialog closes);
// ★ = offered first; Hide = never offered (the file stays)
const MU_ENERGY = {calm: 190, steady: 42, energetic: 330}, MU_TONE = {dark: 255, warm: 25, bright: 55};
const muBed = k => ({room: t('Room tone'), cafe: t('Café'), city: t('City'), nature: t('Nature'), rain: t('Rain'), office: t('Office')})[k] || k;
let MU_TAB = 'song', MU_FILTER = 'all';
function muTime(s) { s = Math.round(s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }
function muStop() { if (MU_AUDIO) MU_AUDIO.pause(); MU_AUDIO = null; MU_PLAYING = ''; $$('[data-mhear]').forEach(b => { b.textContent = '▶'; }); }
function muHear(rel, btn, url) {                           // ▶ / ❚❚ on a song or a bed (url: another sound)
  if (MU_PLAYING === rel) { muStop(); return; }
  muStop();
  try { MU_AUDIO = new Audio(url || '/api/music/hear?rel=' + encodeURIComponent(rel)); MU_AUDIO.onended = muStop;
    MU_AUDIO.play().catch(() => {}); MU_PLAYING = rel; if (btn) btn.textContent = '❚❚'; } catch (e) { /* no sound */ }
}
function muChips(x) {                                       // a song's measures (or a bed's kind) as chips
  if (x.type === 'bed' || x.kind) return `<span class="chip">${esc(muBed(x.kind))}</span>${x.len_s ? `<span class="small dim">${dec(x.len_s, 0)} s</span>` : ''}`;
  return x.bpm ? `<span class="chip mono">${Math.round(x.bpm)} BPM</span><span class="chip mue" style="--h:${MU_ENERGY[x.energy] || 0}" title="${ta('How busy it is: calm, steady or energetic')}">${esc(t(x.energy))}</span>
      <span class="chip mue" style="--h:${MU_TONE[x.tone] || 0}" title="${ta('Its sound: dark, warm or bright')}">${esc(t(x.tone))}</span><span class="small dim mono">${muTime(x.len_s)}</span>`
    : `<span class="small dim">${t('not measured yet')}</span>`;
}
function muUpload(f, type, kind) {                          // a song / bed the user picked -> library\music (a raw body)
  return new Promise((ok, bad) => { const x = new XMLHttpRequest();
    x.open('POST', `/api/music/upload?name=${encodeURIComponent(f.name)}&type=${type}&kind=${encodeURIComponent(kind || '')}`);
    x.setRequestHeader('X-ML-Token', TOKEN); x.setRequestHeader('Content-Type', 'application/octet-stream');
    x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (e) { /* not JSON */ }
      if (x.status < 300) ok(j); else bad(new Error((j && j.error) || `${x.status}`)); };
    x.onerror = () => bad(new Error(t('{name}: the copy stopped - try again', {name: f.name}))); x.send(f); });
}
function motionMusic(body, MU) {
  const measure = async () => { const pre = $('#mulog', body); pre.hidden = false;
    $('#muprog', body).textContent = t('Measuring…');
    try { const j = await api('/api/music/index', {});
      followJob(j.id, pre, () => route(true)); } catch (e) { toast(e.message, 'err'); } };
  const draw = () => {
    const song = MU_TAB === 'song', T = MU.tracks.filter(x => x.type === MU_TAB);
    const L = T.filter(x => MU_FILTER === 'all' ? !x.off : MU_FILTER === 'fav' ? x.fav && !x.off : x.off);
    const n = (typ, f) => MU.tracks.filter(x => x.type === typ && f(x)).length;
    const row = x => `<div class="sdrow murow${x.off ? ' off' : ''}" data-rel="${esc(x.rel)}">
        <button class="btn sm ghost" data-mhear title="${ta('Listen')}">${MU_PLAYING === x.rel ? '❚❚' : '▶'}</button>
        <span class="grow sdname"><b>${esc(x.title)}</b>${x.artist ? ` <span class="muted">${esc(x.artist)}</span>` : ''}</span>
        ${muChips(x)}
        <span class="chip${x.made && /free plan/.test(x.licence) ? ' sdel test' : ''}" title="${esc(x.licence)}">${x.made ? (/free plan/.test(x.licence) ? t('ElevenLabs · non-commercial') : 'ElevenLabs') : esc(t(x.from))}</span>
        <button class="btn sm ghost sdstar${x.fav ? ' on' : ''}" data-fav aria-pressed="${x.fav}" title="${ta('Favourite: offered first in New edit')}">${x.fav ? '★' : '☆'}</button>
        <button class="btn sm ghost" data-off aria-pressed="${x.off}" title="${x.off ? ta('Offer it again') : ta('Hide it: never offered (the file stays)')}">${x.off ? t('Show') : t('Hide')}</button></div>`;
    body.innerHTML = `<div class="row sdtop">
        <span class="row pfilters">${[['song', t('Songs')], ['bed', t('Ambience')]].map(([k, l]) => `<button class="fchip${MU_TAB === k ? ' on' : ''}" data-tab="${k}">${l} <span class="dim">${n(k, x => !x.off)}</span></button>`).join('')}</span>
        <span class="grow"></span>
        ${song ? `<label class="btn pri"><svg class="i"><use href="#i-upload"/></svg>${t('Add songs')}<input type="file" id="mufiles" hidden multiple accept="audio/*,.mp3,.m4a,.wav,.flac,.ogg"></label>
            <button class="btn" id="mulink"><svg class="i"><use href="#i-link"/></svg>${t('A song from a link')}</button>`
          : `<button class="btn pri" id="mumake"><svg class="i"><use href="#i-sparkle"/></svg>${t('Make ambience')}</button>
            <select id="mukind" title="${ta('What kind of ambience the files are')}">${MU.beds.map(k => `<option value="${k}">${esc(muBed(k))}</option>`).join('')}</select>
            <label class="btn"><svg class="i"><use href="#i-upload"/></svg>${t('Add ambience')}<input type="file" id="mufiles" hidden multiple accept="audio/*,.mp3,.m4a,.wav,.flac,.ogg"></label>`}
        ${MU.unmeasured ? `<button class="btn" id="muindex"><svg class="i"><use href="#i-music"/></svg>${tn(MU.unmeasured, 'Measure {n} new', 'Measure {n} new')}</button>` : ''}</div>
      <div class="row sdtop" id="mulinkrow" hidden><input type="text" id="mulinku" placeholder="https://…" style="max-width:460px">
        <button class="btn" id="mulinkgo">${t('Download')}</button><span class="small muted">${t('YouTube, SoundCloud… saved as an MP3 with your downloads')}</span></div>
      <div id="muprog" class="small"></div><div id="mulg" hidden></div><pre class="log" id="mulog" hidden></pre>
      ${T.length ? `<div class="row pfilters" style="margin-bottom:8px">${[['all', t('In use'), n(MU_TAB, x => !x.off)], ['fav', `★ ${t('Favourites')}`, n(MU_TAB, x => x.fav && !x.off)], ['off', t('Hidden'), n(MU_TAB, x => x.off)]].map(([k, l, c]) =>
          `<button class="fchip${MU_FILTER === k ? ' on' : ''}" data-f="${k}">${l} <span class="dim">${c}</span></button>`).join('')}</div>` : ''}
      ${!T.length ? emptyHero(song ? 'music' : 'volume', song ? t('No songs yet') : t('No ambience yet'), song
          ? t('Songs you download in the Analyser (as an MP3) show up here by themselves - or add your own files.')
          : t('A quiet room, a café or a street under your voice - it fills the silence between your cuts. Make one with ElevenLabs or add a file.'), '')
        : !L.length ? `<div class="small muted">${t('Nothing here.')}</div>` : `<div class="mulist">${L.map(row).join('')}</div>`}`;
    $$('[data-tab]', body).forEach(b => b.onclick = () => { MU_TAB = b.dataset.tab; muStop(); draw(); });
    $$('[data-f]', body).forEach(b => b.onclick = () => { MU_FILTER = b.dataset.f; draw(); });
    if ($('#muindex', body)) $('#muindex', body).onclick = measure;
    if ($('#mumake', body)) $('#mumake', body).onclick = () => musicMakeModal(MU, () => route(true));
    if ($('#mulink', body)) $('#mulink', body).onclick = () => { const r = $('#mulinkrow', body); r.hidden = !r.hidden; if (!r.hidden) $('#mulinku', body).focus(); };
    if ($('#mulinku', body)) $('#mulinku', body).onkeydown = e => { if (e.key === 'Enter') $('#mulinkgo', body).click(); };
    if ($('#mulinkgo', body)) $('#mulinkgo', body).onclick = async () => {
      const url = $('#mulinku', body).value.trim(), pre = $('#mulog', body);
      if (!/^https?:\/\//i.test(url)) { toast(t('Paste a full link starting with https://'), 'err'); return; }
      const j = await startJob('download', {url, preset: 'mp3'}, false);
      if (!j) return;
      $('#mulinkgo', body).disabled = true; pre.hidden = false; $('#muprog', body).textContent = t('downloading…');
      followJob(j.id, pre, r => { if (r.status === 'done') measure(); else { $('#muprog', body).textContent = r.login ? '' : t(r.status); $('#mulinkgo', body).disabled = false;
        if (r.login) loginInline($('#mulg', body), r.login, () => $('#mulinkgo', body).click()); } });   // the site wants a login
    };
    $('#mufiles', body).onchange = async e => {
      const files = [...e.target.files].filter(f => !/^\._/.test(f.name)), kind = $('#mukind', body) ? $('#mukind', body).value : '';
      e.target.value = '';
      try {
        for (let i = 0; i < files.length; i++) {
          $('#muprog', body).textContent = t('Copying {n} of {total}…', {n: i + 1, total: files.length});
          await muUpload(files[i], song ? 'song' : 'bed', kind);
        }
        if (files.length) measure();
      } catch (x) { toast(x.message, 'err'); $('#muprog', body).textContent = ''; }
    };
    $$('.murow', body).forEach(r => {
      const x = MU.tracks.find(y => y.rel === r.dataset.rel);
      $('[data-mhear]', r).onclick = e => muHear(x.rel, e.currentTarget);
      const set = async (k, v) => { try { await api('/api/music/set', {rel: x.rel, [k]: v}); x[k] = v; draw(); } catch (e) { toast(e.message, 'err'); } };
      $('[data-fav]', r).onclick = () => set('fav', !x.fav);
      $('[data-off]', r).onclick = () => set('off', !x.off);
    });
  };
  draw();
  onCleanup(muStop);
}
// Music > Make ambience: ElevenLabs beds (15 s that loop with no seam) - the key of Sounds > Make sounds; the credits
// each kind takes, what the month has left; a job, then the Ambience tab
function musicMakeModal(MU, done) {
  const EL = MU.elevenlabs || {}, G = MU.make || {}, want = {};
  Object.keys(G).forEach(k => { want[k] = 0; });
  const left = () => (EL.balance && EL.balance.limit ? EL.balance.limit - (EL.balance.used || 0) : EL.free_credits);
  const credits = () => Object.entries(want).reduce((a, [k, n]) => a + n * ((G[k] || {}).credits || 0), 0);
  modal(`<h2>${t('Make ambience with ElevenLabs')}</h2>
    <p class="hint">${t('15 seconds of a quiet room, a café or a street that loops with no seam. Under your voice it fills the silence between cuts - mixed far under your words.')}</p>
    ${EL.key_set ? '' : `<p class="small bad">${t('Add your ElevenLabs key first: Motion Graphics > Sounds > Make sounds.')}</p>`}
    ${EL.balance && EL.balance.limit ? `<div class="small muted">${t('This month: {used} of {limit} credits used (as of {when})', {used: numLoc(EL.balance.used || 0), limit: numLoc(EL.balance.limit), when: whenStr(EL.balance.when)})}</div>` : ''}
    <div class="sdwant" id="muwant" style="margin-top:10px"></div>
    <div class="row sp" style="margin-top:10px"><span class="small" id="mucost"></span><button class="btn pri" id="mugo">${t('Make them')}</button></div>
    <div class="small" id="muprog2"></div><pre class="log" id="mulog2" hidden></pre>`);
  const draw = () => {
    $('#muwant').innerHTML = Object.entries(G).map(([k, v]) => `<div class="sdw" title="${esc(v.what)}"><span class="grow">${esc(muBed(k))}</span>
      <button class="btn sm ghost" data-dn="${k}" aria-label="${ta('Fewer')}">−</button><b class="mono">${want[k]}</b><button class="btn sm ghost" data-up="${k}" aria-label="${ta('More')}">+</button></div>`).join('');
    const tot = Object.values(want).reduce((a, b) => a + b, 0), cr = credits(), over = EL.plan !== 'paid' && cr > left();
    $('#mucost').innerHTML = `${tn(tot, '{n} bed', '{n} beds')} = ${t('about {n} credits', {n: numLoc(cr)})}${EL.plan !== 'paid' ? ` <span class="${over ? 'bad' : 'muted'}">${t('of {n} left this month', {n: numLoc(left())})}</span>` : ''}`;
    $('#mugo').disabled = !tot || over || !EL.key_set;
    $$('[data-dn]').forEach(b => b.onclick = () => { want[b.dataset.dn] = Math.max(0, want[b.dataset.dn] - 1); draw(); });
    $$('[data-up]').forEach(b => b.onclick = () => { want[b.dataset.up] = Math.min(3, want[b.dataset.up] + 1); draw(); });
  };
  draw();
  $('#mugo').onclick = async () => {
    const go = $('#mugo');
    go.disabled = true;
    try {
      const j = await api('/api/music/beds', {want: Object.fromEntries(Object.entries(want).filter(([, n]) => n > 0))}), pre = $('#mulog2');
      pre.hidden = false; $('#muprog2').textContent = t('Making them - a few seconds each…');
      followJob(j.id, pre, r => { if (r.status === 'done') { toast(t('Your new ambience is under Ambience - listen and keep the best'), 'ok'); MU_TAB = 'bed'; closeModal(); done(); }
        else { $('#muprog2').textContent = t('It did not finish - see the lines above.'); go.disabled = false; } });
    } catch (e) { toast(e.message, 'err'); go.disabled = false; }
  };
}
// Sounds > Make sounds (0.6.0; the user: "the sound effects ... seem very repetitive and AI-made ... connect elevenlabs"):
// the key (kept on this PC, never shown again), the plan (free = no commercial licence), how many of each kind - the
// kinds with few sounds first -, the credits it takes; a job, then the New filter to listen and keep the best
function soundsMakeModal(SD, done) {
  const EL = SD.elevenlabs || {}, G = SD.generate || {}, have = k => SD.sounds.filter(s => s.kind === k && !s.off).length;
  const want = {};
  Object.entries(G).forEach(([k, v]) => { want[k] = have(k) < 6 ? v.n : 0; });
  let plan = EL.plan || 'free';
  const left = () => (EL.balance && EL.balance.limit ? EL.balance.limit - (EL.balance.used || 0) : EL.free_credits);
  const credits = () => Object.entries(want).reduce((a, [k, n]) => a + n * ((G[k] || {}).credits || EL.credits), 0);
  const fit = () => { if (plan !== 'free') return;                         // the free month: what is left of it
    for (const k of Object.keys(want).reverse()) while (credits() > left() && want[k] > 0) want[k]--; };
  fit();
  modal(`<h2>${t('Make sounds with ElevenLabs')}</h2>
    <p class="hint">${t('ElevenLabs makes each sound from a description - every one is different. They go into your library: listen to them under New, star the good ones and hide the rest.')}</p>
    ${EL.balance && EL.balance.limit ? `<div class="small muted">${t('This month: {used} of {limit} credits used (as of {when})', {used: numLoc(EL.balance.used || 0), limit: numLoc(EL.balance.limit), when: whenStr(EL.balance.when)})}</div>` : ''}
    <div class="sdkey" id="sdkey"></div>
    <div class="sdplans">${[['free', t('Free'), t('10,000 credits a month - a short sound takes about 5. Non-commercial use only, and a video you post credits elevenlabs.io.')],
      ['paid', t('Paid'), t('A commercial licence for the videos you post - and you may share the sounds with friends.')]].map(([v, l, d]) =>
      `<button class="necard sdplan" data-plan="${v}"><b>${l}</b><span>${d}</span></button>`).join('')}</div>
    <div class="edlbl">${t('How many of each')}</div>
    <div class="sdwant" id="sdwant"></div>
    <div class="row sp" style="margin-top:10px"><span class="small" id="sdcost"></span><button class="btn pri" id="sdgo">${t('Make them')}</button></div>
    <div class="small" id="sdprog2"></div><pre class="log" id="sdlog2" hidden></pre>`);
  const drawKey = () => { $('#sdkey').innerHTML = EL.key_set && !EL.change
      ? `<span class="small">${t('Your key')} <span class="mono">····${esc(EL.key_end)}</span></span><button class="btn sm ghost" id="sdkeyc">${t('Change')}</button>`
      : `<label class="sdlab">${t('Your ElevenLabs API key (kept on this PC only)')}<input type="password" id="sdkeyi" autocomplete="off" placeholder="sk_…"></label>
         <a class="small" href="https://elevenlabs.io/app/settings/api-keys" target="_blank" rel="noopener">${t('Get a free key')}</a>`;
    if ($('#sdkeyc')) $('#sdkeyc').onclick = () => { EL.change = true; drawKey(); }; };
  const draw = () => {
    $$('.sdplan').forEach(b => b.classList.toggle('on', b.dataset.plan === plan));
    $('#sdwant').innerHTML = Object.entries(G).map(([k, v]) => `<div class="sdw" title="${esc(v.what)}"><span class="eddot" style="--h:${meHue(k)}"></span>
      <span class="grow">${esc(edKind(k))} <span class="small dim">${t('{n} now', {n: have(k)})}</span></span>
      <button class="btn sm ghost" data-dn="${k}" aria-label="${ta('Fewer')}">−</button><b class="mono">${want[k]}</b><button class="btn sm ghost" data-up="${k}" aria-label="${ta('More')}">+</button></div>`).join('');
    const tot = Object.values(want).reduce((a, b) => a + b, 0), cr = credits(), over = plan === 'free' && cr > left();
    $('#sdcost').innerHTML = `${tn(tot, '{n} sound', '{n} sounds')} = ${t('about {n} credits', {n: numLoc(cr)})}${plan === 'free' ? ` <span class="${over ? 'bad' : 'muted'}">${t('of {n} left this month', {n: numLoc(left())})}</span>` : ''}`;
    $('#sdgo').disabled = !tot || over;
    $$('[data-dn]').forEach(b => b.onclick = () => { want[b.dataset.dn] = Math.max(0, want[b.dataset.dn] - 1); draw(); });
    $$('[data-up]').forEach(b => b.onclick = () => { want[b.dataset.up] = Math.min(10, want[b.dataset.up] + 1); draw(); });
  };
  $$('.sdplan').forEach(b => b.onclick = () => { plan = b.dataset.plan; fit(); draw(); });
  drawKey(); draw();
  $('#sdgo').onclick = async () => {
    const go = $('#sdgo'), key = $('#sdkeyi') ? $('#sdkeyi').value.trim() : '';
    if (!EL.key_set && !key) { toast(t('Add your ElevenLabs key first'), 'err'); return; }
    go.disabled = true;
    try {
      await api('/api/sounds/elevenlabs', key ? {key, plan} : {plan});
      const j = await api('/api/sounds/generate', {want: Object.fromEntries(Object.entries(want).filter(([, n]) => n > 0))}), pre = $('#sdlog2');
      pre.hidden = false; $('#sdprog2').textContent = t('Making them - a few seconds each…');
      followJob(j.id, pre, r => { if (r.status === 'done') { toast(t('Your new sounds are under New - listen and keep the best'), 'ok'); closeModal(); done(); }
        else { $('#sdprog2').textContent = t('It did not finish - see the lines above.'); go.disabled = false; } });
    } catch (e) { toast(e.message, 'err'); go.disabled = false; }
  };
}
// Sounds > Add sounds: a folder or files (copied to the lab for the import), or a folder's path (read where it is)
function soundsAddModal(done) {
  modal(`<h2>${t('Add sounds')}</h2>
    <p class="hint">${t('Sounds from a pack MotionLab knows are sorted as its list (only the ones it uses). For other sounds, say where they are from and what their licence allows - each gets its kind from its name.')}</p>
    <div class="row" style="gap:8px;flex-wrap:wrap"><label class="btn"><svg class="i"><use href="#i-folder"/></svg>${t('Pick a folder…')}<input type="file" id="sddir" hidden webkitdirectory multiple></label>
      <label class="btn"><svg class="i"><use href="#i-upload"/></svg>${t('Pick files…')}<input type="file" id="sdfiles" hidden multiple accept="audio/*,.wav,.mp3,.flac,.ogg,.aif,.aiff,.m4a"></label>
      <span class="small muted" id="sdpicked"></span></div>
    <label class="sdlab">${t('Or the folder\'s path - read where it is, nothing copied (for a big pack)')}<input type="text" id="sdpath" placeholder="C:\\Users\\…\\Downloads\\pack"></label>
    <label class="sdlab">${t('Or a link a friend sent you (Google Drive) - their sounds, sorted as theirs')}<input type="text" id="sdlink" placeholder="https://drive.google.com/…"></label>
    <label class="sdlab">${t('Where they are from')}<input type="text" id="sdfrom" maxlength="200" placeholder="${ta('a pack, a site or an author')}"></label>
    <label class="sdlab">${t('What their licence allows')}<input type="text" id="sdlic" maxlength="300" placeholder="${ta('e.g. royalty-free, commercial use, no attribution')}"></label>
    <div class="small muted">${t('Left empty, only the sounds on MotionLab\'s list are added.')}</div>
    <div id="sdprog" class="small"></div><pre class="log" id="sdlog" hidden></pre>
    <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn pri" id="sdgo" disabled>${t('Add them')}</button></div>`);
  const EXT = /\.(wav|mp3|flac|ogg|aif|aiff|m4a)$/i;
  let files = [];
  const ready = () => { $('#sdgo').disabled = !files.length && !$('#sdpath').value.trim() && !$('#sdlink').value.trim(); };
  const pick = list => { files = [...list].filter(f => EXT.test(f.name) && !/^\._/.test(f.name));
    $('#sdpicked').textContent = files.length ? tn(files.length, '{n} sound', '{n} sounds') : t('no sounds in what you picked'); ready(); };
  $('#sddir').onchange = e => pick(e.target.files);
  $('#sdfiles').onchange = e => pick(e.target.files);
  $('#sdpath').oninput = ready;
  $('#sdlink').oninput = ready;
  $('#sdgo').onclick = async () => {
    const go = $('#sdgo'), prog = $('#sdprog'), frm = $('#sdfrom').value.trim(), lic = $('#sdlic').value.trim();
    if (!!frm !== !!lic) { toast(t('Fill in both - where they are from and their licence - or neither'), 'err'); return; }
    go.disabled = true;
    const body = {from: frm, licence: lic};
    try {
      if (files.length) {
        const d = new Date(), p2 = x => String(x).padStart(2, '0');
        body.batch = `${d.getFullYear()}${p2(d.getMonth() + 1)}${p2(d.getDate())}-${p2(d.getHours())}${p2(d.getMinutes())}${p2(d.getSeconds())}-${Math.random().toString(36).slice(2, 6).padEnd(4, '0')}`;
        for (let i = 0; i < files.length; i++) {
          const f = files[i];
          prog.textContent = t('Copying {n} of {total}…', {n: i + 1, total: files.length});
          await new Promise((ok, bad) => { const x = new XMLHttpRequest();
            x.open('POST', `/api/sounds/upload?batch=${body.batch}&path=${encodeURIComponent(f.webkitRelativePath || f.name)}`);
            x.setRequestHeader('X-ML-Token', TOKEN); x.setRequestHeader('Content-Type', 'application/octet-stream');
            x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (e) { /* not JSON */ }
              if (x.status < 300) ok(j); else bad(new Error((j && j.error) || `${x.status}`)); };
            x.onerror = () => bad(new Error(t('{name}: the copy stopped - try again', {name: f.name}))); x.send(f); });
        }
      } else if ($('#sdlink').value.trim()) body.link = $('#sdlink').value.trim();
      else body.folder = $('#sdpath').value.trim();
      prog.textContent = t('Adding them to your library…');
      const j = await api('/api/sounds/import', body), pre = $('#sdlog');
      pre.hidden = false;
      followJob(j.id, pre, r => { prog.textContent = r.status === 'done' ? t('Done.') : t('It did not finish - see the lines above.');
        if (r.status === 'done') { toast(t('Sounds added')); closeModal(); done(); } else go.disabled = false; });
    } catch (e) { toast(e.message, 'err'); prog.textContent = ''; go.disabled = false; }
  };
}
// Motion Graphics > Logos (the logo library, 2026-10-16): every logo with its versions; + picks several for a logo wall
let LG_PICKED = [];
function motionLogos(body, M, D) {
  if (!D.logos.length) {
    body.innerHTML = emptyHero('motion', t('No logos yet'), t('Put SVG logos in refs\\logos (one folder per logo) and ask Claude to add them to the library.'), '');
    return;
  }
  const wall = (M.library || []).find(tp => tp.id === 'logo-wall');
  let q = '', g = '';
  body.innerHTML = `<div class="hint" style="margin-bottom:10px">${t('Real logos of apps, platforms and AI tools for your graphics - sharp at any size, in their own colours or in one colour of yours. In a graphic\'s settings, <b>Pick a logo…</b> puts one in; in a text, write it like <code>:youtube:</code>. They are trademarks of their owners: use them to name the products a video is about.')}</div>
    <div class="lgtray" id="lgtray"></div>
    <div class="row" style="gap:8px;margin:10px 0;flex-wrap:wrap"><input type="search" id="lgq" placeholder="${ta('Search: youtube, editing, ai…')}" style="width:240px">
      <div class="row pfilters" style="margin:0">${[['', t('All|logos')], ...Object.keys(D.groups || {}).map(k => [k, LOGO_GROUPS[k] || k])].map(([k, l]) => `<button class="fchip${k ? '' : ' on'}" data-g="${esc(k)}">${esc(l)} <span class="dim">${k ? D.logos.filter(x => x.group === k).length : D.logos.length}</span></button>`).join('')}</div></div>
    <div class="lggrid big" id="lgall"></div>`;
  const tray = $('#lgtray', body), grid = $('#lgall', body);
  const name = id => (D.logos.find(x => x.id === id) || {name: id}).name;
  const drawTray = () => {
    tray.innerHTML = LG_PICKED.length ? `<span class="small muted">${t('Picked')}</span> ${LG_PICKED.map(id => `<span class="tag lgtag">${esc(name(id))}<button data-unpick="${esc(id)}" title="${ta('Take it out')}">✕</button></span>`).join('')}
      ${wall ? `<button class="btn pri sm" id="lgwall">${t('Make a logo wall with them')}</button>` : ''}<button class="btn sm" id="lgcopy" title="${ta('For a text setting')}">${t('Copy as :logos:')}</button><button class="btn sm" id="lgclr">${t('Clear')}</button>`
      : `<span class="small muted">${t('Pick several with <b>+</b> to make a logo wall from them.')}</span>`;
    $$('[data-unpick]', tray).forEach(b => b.onclick = () => { LG_PICKED = LG_PICKED.filter(x => x !== b.dataset.unpick); drawTray(); drawGrid(); });
    if ($('#lgwall', tray)) $('#lgwall', tray).onclick = () => motionModal(wall, M, {logos: LG_PICKED.join('|'), title: ''});
    if ($('#lgcopy', tray)) $('#lgcopy', tray).onclick = () => copy(LG_PICKED.map(id => `:${id}:`).join(' '));
    if ($('#lgclr', tray)) $('#lgclr', tray).onclick = () => { LG_PICKED = []; drawTray(); drawGrid(); };
  };
  const drawGrid = () => {
    const L = logoFind(D.logos.filter(lg => !g || lg.group === g), q);
    grid.innerHTML = L.map(lg => { const on = LG_PICKED.includes(lg.id);
      return `<div class="mgc lgc${on ? ' on' : ''}" data-id="${esc(lg.id)}" tabindex="0"><button class="lgadd" data-add="${esc(lg.id)}" title="${on ? ta('Picked - click to take it out') : ta('Pick it for a logo wall')}">${on ? '✓' : '+'}</button>
        ${logoTile(lg, '')}<div style="margin-top:6px"><b>${esc(lg.name)}</b></div><div class="small dim">${esc(LOGO_GROUPS[lg.group] || lg.group)} · ${plural(Object.keys(lg.variants).length, 'version')}</div></div>`; }).join('')
      || `<div class="small muted">${t('No logo fits those words.')}</div>`;
  };
  grid.onclick = grid.onkeydown = e => {
    if (e.type === 'keydown' && e.key !== 'Enter') return;
    const a = e.target.closest('[data-add]');
    if (a) { e.stopPropagation(); LG_PICKED = LG_PICKED.includes(a.dataset.add) ? LG_PICKED.filter(x => x !== a.dataset.add) : [...LG_PICKED, a.dataset.add].slice(0, 12); drawTray(); drawGrid(); return; }
    const c = e.target.closest('.lgc');
    if (c) logoModal(D.logos.find(x => x.id === c.dataset.id), () => { drawTray(); drawGrid(); });
  };
  const qi = $('#lgq', body);
  qi.oninput = () => { q = qi.value; drawGrid(); };
  $$('[data-g]', body).forEach(b => b.onclick = () => { g = b.dataset.g; $$('[data-g]', body).forEach(x => x.classList.toggle('on', x === b)); drawGrid(); });
  drawTray();
  drawGrid();
}
function logoModal(lg, after) {
  const vs = Object.keys(lg.variants);
  modal(`<div class="row" style="gap:10px;padding-right:28px"><h2 style="margin:0">${esc(lg.name)}</h2><span class="chip">${esc(LOGO_GROUPS[lg.group] || lg.group)}</span></div>
    <p class="small muted" style="margin:6px 0 12px">${t('In a logo setting write <code>{id}</code> - the graphic picks the version that stands out on its background - or one version below. In a text write <code>:{id}:</code>.', {id: esc(lg.id)})}</p>
    <div class="lgvars">${vs.map(v => `<div class="lgvar"><div class="lgpair"><span class="lgimg"><img src="${logoSrc(lg, v)}" alt=""></span><span class="lgimg dk"><img src="${logoSrc(lg, v)}" alt=""></span></div>
      <div class="small"><b>${esc(v)}</b> <span class="muted">- ${esc(LOGO_VARIANT[v] || v)}</span></div>
      <div class="row" style="gap:6px;margin-top:4px"><code class="small">${esc(lg.id)}/${esc(v)}</code><button class="btn sm" data-copy="${esc(lg.id)}/${esc(v)}">${t('Copy')}</button></div></div>`).join('')}</div>
    <div class="row" style="margin-top:14px"><button class="btn pri" id="lgpick">${LG_PICKED.includes(lg.id) ? t('Picked for a logo wall - take it out') : t('Pick it for a logo wall')}</button><button class="btn" data-copy=":${esc(lg.id)}:">${t('Copy :{id}:', {id: esc(lg.id)})}</button></div>
    <div class="small dim" style="margin-top:10px">${t('A trademark of its owner - use it to name the product your video is about.')}</div>`, el => {
    $$('[data-copy]', el).forEach(b => b.onclick = () => copy(b.dataset.copy));
    $('#lgpick', el).onclick = () => { LG_PICKED = LG_PICKED.includes(lg.id) ? LG_PICKED.filter(x => x !== lg.id) : [...LG_PICKED, lg.id].slice(0, 12); closeModal(); after(); };
  });
}
function motionClips(body, M, clips) {
  let kf = '', sf = '';
  const kinds = [...new Set(clips.map(c => c.kind))];
  const draw = () => {
    const shown = clips.filter(c => (!kf || c.kind === kf) && (!sf || mclipStatus(c) === sf || (sf === 'p3' && c.still)));
    body.innerHTML = `<div class="hint" style="margin-bottom:10px">${t('The template clips you captured (they stay on this PC, untouched). MotionLab measured each one with no Claude - its moves with frame + timecode, the ease of each, how long it holds - and Claude wrote what it is and whether it is worth rebuilding. Hover a clip to play it.')}</div>
      <div class="row pfilters">${[['', t('All|clips')], ...kinds.map(k => [k, k.replace(/-/g, ' ')])].map(([k, l]) => `<button class="fchip${k === kf ? ' on' : ''}" data-k="${esc(k)}">${esc(l)} <span class="dim">${k ? clips.filter(c => c.kind === k).length : clips.length}</span></button>`).join('')}</div>
      <div class="row pfilters">${MSTATUS.map(([k, l]) => `<button class="fchip sm${k === sf ? ' on' : ''}" data-s="${k}">${l} <span class="dim">${k ? clips.filter(c => mclipStatus(c) === k || (k === 'p3' && c.still)).length : clips.length}</span></button>`).join('')}</div>
      <div class="mcgrid">${shown.map(c => { const s = mclipStatus(c);
        return `<div class="mcc" data-id="${esc(c.pack + '/' + c.id)}" tabindex="0">
        <div class="mcpic">${c.poster ? `<img src="${fileUrl(c.poster)}" alt="" loading="lazy" style="width:100%;height:100%;object-fit:contain;display:block">` : ''}</div>
        <div class="row sp" style="margin-top:6px"><b class="small">${esc(c.name)}</b><span class="mst mst-${s}">${MSTATUS_WORD[s]}</span></div>
        <div class="small muted mgwhat">${esc((c.card || {}).what || '')}</div>
        <div class="small dim">${dec(c.seconds, 1)} s · ${c.still ? t('no motion caught') : plural(c.moves, 'move')}${c.loops ? ` · ${t('loops')}` : ''}</div></div>`; }).join('') || `<div class="empty">${t('Nothing here.')}</div>`}</div>`;
    $$('[data-k]', body).forEach(b => b.onclick = () => { kf = b.dataset.k; draw(); });
    $$('[data-s]', body).forEach(b => b.onclick = () => { sf = b.dataset.s; draw(); });
    // a picture per card (a lazy <img>: a video's poster loads at once, for hundreds of clips), the clip itself made
    // on the first hover and kept (it goes on where it stopped, as before)
    $$('.mcc', body).forEach(card => {
      let v = null;
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
        card.onmouseenter = () => {
          if (!v) {
            const c = clips.find(x => x.pack + '/' + x.id === card.dataset.id);
            v = document.createElement('video');
            Object.assign(v, {muted: true, loop: true, playsInline: true, src: fileUrl(c.file)});
            if (c.poster) v.poster = fileUrl(c.poster);
            $('.mcpic', card).replaceChildren(v);
          }
          v.play().catch(() => {});
        };
        card.onmouseleave = () => { if (v) v.pause(); };
      }
      card.onclick = card.onkeydown = e => { if (e.type === 'keydown' && e.key !== 'Enter') return; motionClipModal(clips.find(c => c.pack + '/' + c.id === card.dataset.id), M); };
    });
  };
  draw();
}
// one template: its live preview (the page's own GSAP, the form's values - nothing rendered, nothing saved), what it
// is for, the clips it was learned from playing beside it; Use in a video / Make a video with it
function motionModal(tp, M, init) {
  const S = (tp.settings || []).map(s => ({...s, value: init && s.id in init ? init[s.id] : s.default}));
  modal(`<div class="mgm"><div class="mgprev" id="mgprev"></div>
    <div><div class="row" style="gap:10px;padding-right:28px"><h2 style="margin:0">${esc(t(tp.name))}</h2><span class="chip">${esc(mkind(tp.kind))}</span></div>
      <p style="margin:8px 0">${esc(t(tp.what || ''))}</p>
      ${(tp.use_for || []).length ? `<div class="small muted">${t('Good for: {tags}', {tags: tp.use_for.map(u => `<span class="tag">${esc(u)}</span>`).join(' ')})}</div>` : ''}
      ${tp.motion ? `<div class="small muted" style="margin-top:4px">${t('Motion: {motion} · {frames} frames at {fps} fps, {w}×{h} - it takes any size', {motion: esc(tp.motion), frames: tp.frames, fps: tp.fps, w: tp.width, h: tp.height})}</div>` : ''}
      <div class="row" style="margin-top:12px"><button class="btn pri" id="mguse">${t('Use in a video…')}</button><button class="btn" id="mggen"><svg class="i"><use href="#i-claude"/></svg>${t('Make a video with it')}</button></div>
      <h3>${t('Try your words')}</h3><div class="small muted" style="margin:-2px 0 6px">${t('The preview follows at once; these values go with it into a video.')}</div>
      <div class="gset">${S.map(s => `<label title="${esc(s.id)}">${esc(t(s.label || s.id))}</label><div>${gsetInput(s)}</div>`).join('')}</div>
      ${(tp.sources || []).length ? `<h3>${t('Learned from')}</h3><div class="mgsrc">${tp.sources.map(s => `<div class="mgs">${s.file ? `<video src="${fileUrl(s.file)}" muted loop autoplay playsinline></video>` : ''}
        <div class="small"><b>${esc((s.clip || '').replace(/^[\w-]+?__/, '').replace(/-/g, ' '))}</b><div class="muted">${esc(s.what || '')}</div></div></div>`).join('')}</div>`
        : `<h3>${t('A MotionLab original')}</h3><div class="small muted">${tp.origin ? t('Not learned from a clip: made for one of the template kinds creators use most ({origin}).', {origin: esc(tp.origin.split(' - ')[0])})
          : t('Not learned from a clip: made for one of the template kinds creators use most.')}</div>`}
    </div></div>`, el => {
    const vals = () => { const v = mdefaults(tp); $$('[data-set]', el).forEach(i => { v[i.dataset.set] = gsetValue(i); }); return v; };
    const live = livePreview($('#mgprev', el), tp, vals);
    const stop = live.stop;
    $$('[data-set]', el).forEach(i => { i.oninput = i.onchange = () => live.refresh(); });
    $$('.mgs video', el).forEach(v => { if (matchMedia('(prefers-reduced-motion: reduce)').matches) v.removeAttribute('autoplay'); });
    $('#mguse', el).onclick = () => { stop(); motionUseModal(tp, vals(), () => motionModal(tp, M)); };
    $('#mggen', el).onclick = () => { stop(); generateModal('graphics', {templates: [tp.id]}); };
  }, 'wide');
}
async function motionUseModal(tp, values, back) {
  const ps = (await api('/api/projects')).filter(p => !inGenerator(p) || p.plans.length);
  const changed = Object.fromEntries(Object.entries(values).filter(([k, v]) => v !== mdefaults(tp)[k]));
  // an overlay (a button, a pin, a like...) goes over the footage: see-through unless the user painted it on purpose
  if (tp.overlay && !('background' in changed) && (tp.settings || []).some(s => s.id === 'background')) changed.background = false;
  modal(`<h2>${t('Use “{name}” in a video', {name: esc(t(tp.name))})}</h2>
    <div class="small muted">${t('A copy goes into the video, sized like its edit (or {w}×{h} without one) and rendered right away; change it later on the video\'s Graphics tab.', {w: tp.width, h: tp.height})}${tp.overlay ? ' ' + t('It goes over your footage, see-through.') : ''}</div>
    ${ps.length ? `<div class="row" style="margin-top:12px"><label>${t('Video')} <select id="muv">${ps.map(p => `<option value="${esc(p.name)}">${esc(p.label || p.name)}</option>`).join('')}</select></label>
      <label>${t('Name')} <input id="mun" value="${esc(tp.id)}" style="width:200px"></label></div>
      ${Object.keys(changed).length ? `<div class="small" style="margin-top:6px">${t('With your words: {tags}', {tags: Object.entries(changed).map(([k, v]) => `<span class="tag">${esc(k)}: ${esc(String(v)).slice(0, 40)}</span>`).join(' ')})}</div>` : ''}
      <div class="row" style="margin-top:12px"><button class="btn pri" id="mugo">${t('Add and render')}</button><span id="mumsg" class="small"></span></div><pre class="log" hidden></pre>`
      : `<div class="empty" style="margin-top:12px">${t('No videos yet - start one in the Editor.')}</div>`}`, m => {
    const go = $('#mugo', m);
    if (!go) return;
    go.onclick = async () => {
      const project = $('#muv', m).value, name = $('#mun', m).value.trim();
      const j = await startJob('overlay_new', {project, graphic: tp.id, name, values: changed}, false);
      if (!j) return;
      go.disabled = true; const pre = $('pre.log', m); pre.hidden = false;
      followJob(j.id, pre, jj => {
        if (jj.status === 'done') { closeModal(); location.hash = `#/project/${encodeURIComponent(project)}/graphics`; }
        else { $('#mumsg', m).innerHTML = `<span class="bad">${t('did not work - see the log')}</span>`; go.disabled = false; }
      });
    };
  });
  modalBack(back);
}
function motionClipModal(c, M) {
  const tpl = M.library.filter(tp => c.built.includes(tp.id)), card = c.card || {};
  const pct = Math.round(100 * (c.moving_share || 0));
  const moves = c.loops ? tn(c.moves, '{n} move, moving {pct} % of the time, loops', '{n} moves, moving {pct} % of the time, loops', {pct})
    : tn(c.moves, '{n} move, moving {pct} % of the time', '{n} moves, moving {pct} % of the time', {pct});
  const eases = t('eases: {eases}', {eases: Object.entries(c.eases || {}).map(([k, n]) => `${esc(t(k))} ×${n}`).join(', ') || '-'});
  modal(`<div class="mgm"><div class="mgprev"><video src="${fileUrl(c.file)}" controls loop autoplay muted playsinline style="width:100%;max-height:560px;border-radius:8px;background:#000"></video></div>
    <div><div class="row" style="gap:10px;padding-right:28px"><h2 style="margin:0">${esc(c.name)}</h2><span class="mst mst-${mclipStatus(c)}">${MSTATUS_WORD[mclipStatus(c)]}</span></div>
      <div class="small muted" style="margin-top:4px">${t('{kind} · {frames} frames at {fps} fps ({s} s) · {w}×{h}', {kind: esc(c.kind.replace(/-/g, ' ')), frames: c.frames, fps: c.fps, s: dec(c.seconds, 2), w: c.width, h: c.height})}</div>
      ${card.what ? `<p style="margin:10px 0"><span class="clchip">Claude</span> ${esc(card.what)}</p>` : ''}
      ${(card.use_for || []).length ? `<div class="small muted">${t('Good for: {tags}', {tags: card.use_for.map(u => `<span class="tag">${esc(u)}</span>`).join(' ')})}</div>` : ''}
      ${card.note ? `<div class="small muted" style="margin-top:4px">${esc(card.note)}</div>` : ''}
      ${tpl.length ? `<div style="margin-top:10px">${t('Rebuilt as {links}', {links: tpl.map(tp => `<a href="#/motion/templates/${esc(tp.id)}">${esc(t(tp.name))}</a>`).join(', ')})}</div>` : ''}
      <h3>${t('Measured by MotionLab')} <span class="mlchip">${t('MotionLab · no Claude')}</span></h3>
      <div class="small">${c.still ? t('A still capture: the clip has fewer than 15 frames, so no motion was caught.')
        : `${moves}; ${eases}${c.alive_in_holds != null ? '; ' + t('something still moves in {pct} % of the holds', {pct: Math.round(100 * c.alive_in_holds)}) : ''}.`}</div>
      ${c.sheet ? `<div style="margin-top:8px"><img src="${fileUrl(c.sheet)}" alt="${ta('contact sheet')}" class="mgsheet" title="${ta('every move\'s start / fastest / end frame, frame + timecode - click to enlarge')}"></div>` : ''}
      ${(c.colours || {}).main ? `<div class="row" style="margin-top:8px;gap:4px">${c.colours.main.map(([h, s]) => `<span class="sw" title="${esc(h)} ${Math.round(100 * s)} %" style="width:22px;height:22px;border-radius:4px;background:${esc(h)};display:inline-block;border:1px solid var(--line2)"></span>`).join('')}</div>` : ''}
    </div></div>`, el => {
    const im = $('.mgsheet', el);
    if (im) im.onclick = () => lightbox([{src: c.sheet, cap: t('{id} - contact sheet', {id: c.id})}], 0);
  }, 'wide');
}

const PFILTERS = [['', t('All|prompts')], ['tool', t('Needs another tool')], ['own', t('No other tool')], ['todo', t('Not checked yet')]];
const pfilterOk = (p, f) => !f || (f === 'tool' ? !!ptool(p) : f === 'own' ? !ptool(p) : !p.structure && !p.review);
async function pagePrompts(main, arg) {               // every kind in one grid; a click opens the prompt
  await api('/api/script/tidy', {}).catch(() => {});     // an improved script replaces its paste (Improve my script)
  const ctx = {R: await api('/api/prompts')};
  let q = '', pf = '';
  try { pf = localStorage.getItem('ml.pfilter') || ''; } catch (e) { /* no storage: all */ }
  if (!PFILTERS.some(([k]) => k === pf)) pf = '';
  const any = ctx.R.items.length;
  main.innerHTML = `<div class="head"><div><div class="crumb"><a href="#/generate">${t('Generator')}</a> /</div><h1>${t('Prompt library')}</h1><div class="sub">${t('Briefs for Claude, prompts for AI video and image tools, hooks and scripts. Click one to open it.')}</div></div>
      ${any ? `<div class="row"><input type="search" id="pq" placeholder="${ta('Search your prompts…')}" style="width:230px"><button class="btn pri" id="padd">${t('Add prompts')}</button>
        <button class="btn" data-open="${esc(ctx.R.folder)}" data-reveal><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>` : ''}</div>
    ${any ? '<div class="row pfilters" id="pfil"></div><div id="ptodo"></div>' : ''}<div id="plist" class="pgrid"></div>`;
  if (!any) {
    $('#plist', main).className = '';
    $('#plist', main).innerHTML = emptyHero('prompts', t('Keep your best prompts here'), t('Paste one you use, attach a creator\'s guide, or let Claude write one from zero. Claude checks each part and helps you improve it.'),
      `<button class="btn pri big" id="padd">${t('Add prompts')}</button>`);
    $('#padd', main).onclick = () => addPromptsModal(ctx.R);
    return;
  }
  $('#padd', main).onclick = () => addPromptsModal(ctx.R);
  const row = p => promptCard(p, ctx.R);
  const draw = () => {
    const all = ctx.R.items, list = $('#plist', main);
    $('#pfil', main).innerHTML = PFILTERS.map(([k, l]) => { const n = all.filter(p => pfilterOk(p, k)).length;
      return k && !n ? '' : `<button class="fchip${k === pf ? ' on' : ''}" data-pf="${k}">${l} <span class="dim">${n}</span></button>`; }).join('');
    $$('[data-pf]', main).forEach(b => b.onclick = () => { pf = b.dataset.pf; try { localStorage.setItem('ml.pfilter', pf); } catch (e) { /* not kept */ } draw(); });
    const todo = all.filter(p => pfilterOk(p, 'todo')).map(p => p.id);
    $('#ptodo', main).innerHTML = pf === 'todo' && todo.length ? `<div class="small muted pftodo">${t('Claude reads each one and marks what is clear, vague or missing, with a tip.')} ${todo.length === 1 ? claudeBtn(optCmd({id: todo[0], kind: todo[0].split('-')[0]}), t('Optimize with Claude'), optTask({kind: todo[0].split('-')[0]}), todo[0]) : claudeBtn(`/write-prompt analyse ${todo.join(' ')}`, t('Check these {n} with Claude', {n: todo.length}), 'prompt', 'analyse')}</div>` : '';
    const items = all.filter(p => pfilterOk(p, pf) && (!q || [p.id, p.title, p.title_auto, p.text, p.model, (p.source || {}).creator, KSHORT[p.kind], ...(p.tags || [])].join(' ').toLowerCase().includes(q)))
      .sort((a, b) => (b.updated || b.added || '').localeCompare(a.updated || a.added || '') || b.id.localeCompare(a.id));
    list.innerHTML = items.map(row).join('') || `<div class="empty">${q ? t('No prompt matches the search.') : t('Nothing here.')}</div>`;
    $$('.pgc', list).forEach(c => c.onclick = () => promptModal(c.dataset.id, ctx));
  };
  ctx.draw = draw;
  ctx.reload = async () => { ctx.R = await api('/api/prompts'); draw(); };
  const pq = $('#pq', main);
  pq.oninput = debounce(() => { q = pq.value.trim().toLowerCase(); draw(); }, 150);
  draw();
  if (arg && /^[a-z]+-\d+$/.test(arg)) {               // #/prompts/<id> (a link from a video, an optimized version): open it
    history.replaceState(null, '', '#/prompts');
    promptModal(arg, ctx);
  }
}
