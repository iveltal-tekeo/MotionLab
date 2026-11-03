/* MotionLab app - js/video-publish.js: a video's Footage, Publish (the ready-to-post package), Graphics, Resolve.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ---- Footage: the user's clips (read-only) + the storyboards (one frame per second of every clip)
function projFootage(el, P) {
  el.innerHTML = `<div class="row sp" style="margin-bottom:12px"><div class="hint">${t("Your clips - only read, never changed. Copy more into the video's folder; the next edit can use them.")}</div>
      <button class="btn sm" data-open="${esc('projects/' + P.name)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>
    <div class="panel"><table class="t"><thead><tr><th>${t('ID')}</th><th>${t('File')}</th><th>${t('Format')}</th><th class="num">${t('Length')}</th><th class="num">${t('Size')}</th></tr></thead><tbody>
    ${P.sources.map(s => `<tr><td class="mono amber">${s.id || '–'}</td><td>${esc(s.name)}${s.exists ? '' : ` <span class="bad">${t('missing|file')}</span>`}</td>
      <td class="small muted">${s.photo ? `<b class="nephoto inl">${t('PHOTO')}</b>${s.resolution ? ' ' + esc(s.resolution) : ''}` : s.resolution ? `${esc(s.resolution)} · ${s.fps || '?'} fps` : t('measured when an edit uses it')}</td>
      <td class="num">${s.duration_s ? dec(s.duration_s, 1) + ' s' : '–'}</td><td class="num">${bytes(s.size)}</td></tr>`).join('')}</tbody></table></div>
    ${P.boards.length ? `<h3>${t('Storyboards (one frame per second of every clip)')}</h3>
    <div class="sheets" style="grid-template-columns:repeat(3,1fr)">${P.boards.map((b, i) => `<img src="${fileUrl(b)}" data-i="${i}" loading="lazy">`).join('')}</div>` : ''}`;
  $$('.sheets img', el).forEach(img => img.onclick = () => lightbox(P.boards.map(b => ({src: b})), +img.dataset.i));
}

// ---- Edit > a video > Publish (0.4.3): the ready-to-post package in build\publish\ - the title, thumbnails A / B / C
// (16:9 + the 9:16 cover, each checked: tools\thumbnail.py), the description with chapters, hashtags (tools\publish.py).
// The app reads package.json (GET /api/project/<p>/publish), runs the thumbnail jobs and calls publish.write
// (POST .../publish); Claude does all of it with /write-title package <p>
const THUMB_JOBS = ['thumb_candidates', 'thumb_make', 'thumb_render', 'thumb_check'];
const PUBST = {};                 // per video: the *do it yourself* choices survive the redraw when a job ends
const CHECK_WORDS = {readability: t('Readable on a phone'), words: t('2-4 words'), text_size: t('Text size'), contrast: t('Contrast'),
  subject: t('Face size'), look: t('Brightness and colour vs your niche'), safe_zone: t('Clear of the apps\' buttons and crops'),
  file_size: t('File size'), title_length: t('Title length on a phone'), title_repeat: t('Adds to the title'), promise: t('The title\'s promise in the first 3 s')};
const CK = {PASS: ['✓', 'ok'], WARN: ['~', 'amber'], FAIL: ['✗', 'bad'], SKIP: ['–', 'dim']};
// x.text = thumbnail.py's sentence, stored in package.json in English: a fixed one shows in Spanish by key (_by_key)
const ckLine = x => { const [ic, cls] = CK[x.status] || ['•', ''], txt = esc(t(x.text ?? ''));
  return `<li><b class="${cls}" title="${esc(x.status)}">${ic}</b><span><b>${esc(CHECK_WORDS[x.rule] || x.rule)}</b>${x.value != null ? ` <span class="ckv">${esc(x.value)}</span>` : ''}
    <span class="muted">${x.status === 'SKIP' ? t('not measured - {text}', {text: txt}) : txt}</span></span></li>`; };
const ckSum = res => res ? `<span class="ckres ${(CK[res] || [])[1] || ''}">${res === 'PASS' ? t('✓ passes') : res === 'WARN' ? t('~ could be better') : res === 'FAIL' ? t('✗ needs a fix') : esc(res)}</span>` : '';
function ckBlock(tm) {
  const c = tm.check || {};
  if (!c['16x9']) return `<div class="small muted">${c.stale ? t('Changed since the last check - <b>Check them</b> above.') : t('Not checked yet - <b>Check them</b> above.')}</div>`;
  return [['16x9', 'YouTube 16:9'], ['9x16', t('Cover 9:16')]].map(([k, l]) => {
    const L = c[k] || [], bad = L.filter(x => x.status === 'FAIL' || x.status === 'WARN');
    return `<div class="ckbox"><div class="row sp"><b class="small">${l}</b><span class="small">${['PASS', 'WARN', 'FAIL', 'SKIP'].map(s => { const n = L.filter(x => x.status === s).length;
        return n ? `<span class="${CK[s][1]}">${CK[s][0]} ${n}</span>` : ''; }).join(' ')}</span></div>
      ${bad.length ? `<ul class="cklist">${bad.map(ckLine).join('')}</ul>` : ''}
      <details><summary class="small muted">${tn(L.length, 'All {n} rules', 'All {n} rules')}</summary><ul class="cklist">${L.map(ckLine).join('')}</ul></details></div>`; }).join('')
    + `<div class="small dim">${c.title ? t('checked {date} with the title “{title}”', {date: esc(c.date || ''), title: esc(c.title)}) : t('checked {date}', {date: esc(c.date || '')})}</div>`;
}
const ytOf = (f, fps) => { const s = Math.floor(f / fps + 1e-9); return s >= 3600 ? `${Math.floor(s / 3600)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}` : `${Math.floor(s / 60)}:${pad(s % 60)}`; };
async function projPublish(el, P) {
  const I = await api(`/api/project/${encodeURIComponent(P.name)}/publish`);
  const pk = I.package || {}, th = pk.thumbnails || [], cand = pk.candidates || {}, items = cand.items || [];
  const S = PUBST[P.name] = PUBST[P.name] || {words: '', template: 'outline', id: '', pick: null, self: false, from: 'clips'};
  const fps = I.fps || (pk.chapters || {}).fps || 30;
  const url = `/api/project/${encodeURIComponent(P.name)}/publish`;
  const claude = (cls = 'pri') => claudeBtn(`/write-title package ${P.name}`, t('Make it with Claude'), 'title', P.name, cls);
  const empty = !I.exists && !I.records.length && !S.self;
  // since 2026-10-15 on the Overview, under the video (the user: "if we are happy with the edit the next row ... the publish
  // tab should not exist and be moved down to the preview video in the overview tab")
  const head = `<div class="pvsech"><svg class="i"><use href="#i-thumb"/></svg><div><h2>${t('Happy with it? Ready to post')}</h2>
    <div class="small muted">${t('The title, thumbnails for YouTube and the vertical cover, the description with chapters and hashtags - checked before you post.')}</div></div></div>`;
  if (empty) {
    el.innerHTML = `${head}${postBox(I)}<div class="panel pbsec pbempty">${claudeBtn(`/write-title package ${P.name}`, t('Make the package with Claude'), 'title', P.name, 'pri big')}
      <span class="small muted">${t('Claude picks the moments, makes and checks three thumbnails and writes the words.')}</span><a href="#" class="small" id="pbself">${t('or do it yourself')}</a></div>
      ${packagingBox(P)}`;
    $('#pbself', el).onclick = e => { e.preventDefault(); S.self = true; projPublish(el, P); };
    wirePackaging(el, P); reIndex(P, I);
    return I;
  }
  // the titles to choose from: the package's own, then the linked title records' (Prepare > Title & thumbnail first)
  const choices = (pk.titles || []).map(x => ({...x}));
  I.records.forEach(r => (r.titles || []).forEach(x => { if (!choices.some(c => c.text === x.text)) choices.push({...x, from: r.id}); }));
  const title = pk.title || '', chs = ((pk.chapters || {}).items || []).map(c => ({f: c.f, name: c.name}));
  const desc = pk.description || {}, tags = pk.hashtags || {};
  if (!S.id) S.id = ['A', 'B', 'C'].find(x => !th.some(y => y.id === x)) || 'A';
  const runJob = async (kind, args) => {
    try { const j = await api('/api/jobs', {kind, args: {project: P.name, ...args}, queue: true});
      toast(j.status === 'queued' ? t('Waiting its turn: {title}', {title: j.title}) : t('Started: {title}', {title: j.title}), 'ok'); ping(); route(); }
    catch (e) { toast(e.message, 'err'); }
  };
  const concept = I.records.flatMap(r => r.concepts || []);
  // the title, the thumbnails and making one yourself = one glowing box (the user, 2026-10-15: "all in one so the person
  // isn't thrown around on where everything is")
  el.innerHTML = `${head}${postBox(I)}<div class="toprow">${claude()}
      <span class="small muted">${t('Claude picks the moments, makes and checks the thumbnails and writes the words. Or do any part yourself below.')}</span></div>
    <div class="panel pbsec pbpack"><div class="pbpart" id="pb-title"><div class="row sp"><h2>${t('Title')}</h2>${title ?`<span class="row" style="gap:6px">${tchars(title.length)}<button class="btn sm" data-cp="title"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy')}</button></span>` : ''}</div>
      ${title ? `<div class="pbtitle">${esc(title)}</div>` : `<div class="small muted">${t('No title yet - pick one below or type your own.')}</div>`}
      ${choices.length ? `<details class="pbchoices"${title ? '' : ' open'}><summary class="small">${tn(choices.length, '{n} title to choose from', '{n} titles to choose from')}</summary>
        <div class="ttlist">${choices.map((c, i) => `<div class="ttrow${c.text === title ? ' chosen' : ''}"><div class="grow"><b class="ttx">${esc(c.text)}</b>
          <div class="small">${c.pattern ? `<span class="ttpat">${esc(c.pattern)}</span> ` : ''}${tchars(c.chars || c.text.length)}</div></div>
          ${c.text === title ? `<span class="tag done">${t('chosen|title')}</span>` : `<button class="btn sm" data-pick="${i}">${t('Use this')}</button>`}</div>`).join('')}</div></details>` : ''}
      <div class="row" style="margin-top:8px"><input type="text" id="pbown" placeholder="${ta('or type your own title')}" maxlength="100" style="flex:1;min-width:260px"><span class="small muted" id="pbownn"></span><button class="btn sm" id="pbownok">${t('Save title')}</button></div></div>
    <div class="pbpart" id="pb-thumbs"><div class="row sp"><h2>${t('Thumbnails')}</h2><span class="row" style="gap:6px">${th.length ? `<button class="btn sm" id="pbcheck" title="${title ? ta('with the title') : ta('no title yet: the title rules are skipped')}">${t('Check them')}</button>` : ''}</span></div>
      ${th.length ? `<div class="pbthumbs">${th.map(tm => { const ph = (tm.photos || [])[0] || {}, v = tm.v ? `?v=${tm.v}` : '';
        return `<div class="pbthumb" data-t="${esc(tm.id)}"><div class="row sp"><span class="row" style="gap:8px"><span class="tid">${esc(tm.id)}</span><b>${esc(tm.words || '')}</b>
            <span class="small muted">${esc(tm.template || '')}${ph.frame != null ? ` · ${ph.clip ? esc(ph.clip) + ' ' : ''}${ftc(ph.frame, ph.fps || 25)}` : ph.image || ph.file ? ` · ${t('your picture')}` : ''}</span></span>${ckSum((tm.check || {}).result)}</div>
          <div class="pbimgs"><figure><img src="${fileUrl(tm.files['16x9'])}${v}" data-lb="16x9" alt=""><figcaption>YouTube 16:9</figcaption></figure>
            <figure class="tall"><img src="${fileUrl(tm.files['9x16'])}${v}" data-lb="9x16" alt=""><figcaption>${t('Cover 9:16')}</figcaption></figure>
            ${tm.files['9x16_crops'] ? `<figure class="crops"><img src="${fileUrl(tm.files['9x16_crops'])}${v}" data-lb="9x16_crops" alt=""><figcaption>${t('How the apps crop it')}</figcaption></figure>` : ''}</div>
          <div class="pbck">${ckBlock(tm)}</div>
          <div class="row" style="margin-top:8px">${tm.settings.length ? `<button class="btn sm" data-tset>${t('Change it…')}</button>` : ''}<button class="btn sm" data-trender>${t('Render again')}</button>
            <button class="btn sm ghost" data-open="${esc(tm.files['16x9'])}" data-reveal>${t('Show in folder')}</button></div></div>`; }).join('')}</div>`
        : `<div class="small muted">${t("No thumbnails yet - Claude makes three (A, B, C) for YouTube's own test, or make one yourself below.")}${I.face_detector ? '' : ' ' + t('Face sizes are not measured on this PC (the face finder is not installed).')}</div>`}</div>
    <details class="pbpart pbself" id="pb-self"${th.length && !S.pick ? '' : ' open'}><summary><h2>${t('Make a thumbnail yourself')}</h2></summary>
      <div class="nestep"><b>1</b>${t('The picture')}</div>
      <div class="row"><button class="btn" id="pbcand"><svg class="i"><use href="#i-analyze"/></svg>${t('Find good moments')}</button>
        ${I.render && I.clips ? `<div class="seg" id="pbfrom"><button data-v="clips">${t('in your clips')}</button><button data-v="render">${t('in the finished video')}</button></div>` : ''}
        <span class="small muted">${t('or')}</span><label class="btn ghost">${t('Use a picture you made…')}<input type="file" id="pbimg" accept=".jpg,.jpeg,.png,.webp" hidden></label>
        <span class="small muted">${t('The image prompt: <a href="#" id="pbai">write it with Claude</a> (Prompts → Image), make it on the site, bring the picture here.')}</span></div>
      ${items.length || I.images.length ? `<div class="pbtiles">${items.map(c => `<button class="pbtile${S.pick && S.pick.c === c.id ? ' on' : ''}" data-c="${esc(c.id)}" title="${ta('score {score}', {score: numStr(c.score)})}${c.face != null ? ` · ${ta('face {face} % of the height', {face: Math.round(c.face * 100)})}` : ''}">
          <img src="${fileUrl(c.png)}" loading="lazy" alt=""><span>${esc(c.clip)} ${ftc(c.frame, c.fps)}</span></button>`).join('')}
        ${I.images.map(m => `<button class="pbtile${S.pick && S.pick.image === m.path ? ' on' : ''}" data-img="${esc(m.path)}" title="${esc(m.name)}"><img src="${fileUrl(m.rel)}" loading="lazy" alt=""><span>${t('your picture')}</span></button>`).join('')}</div>
        ${cand.made ? `<div class="small dim">${cand.from === 'render' ? t('moments found {date} in the finished video', {date: esc(cand.made)}) : t('moments found {date} in the clips', {date: esc(cand.made)})}${cand.face_detector ? '' : ` · ${t('faces not measured')}`}</div>` : ''}` : ''}
      <div class="nestep"><b>2</b>${t('The words and the design')}</div>
      <div class="nedet spf"><label>${t('2-4 words')}</label><div class="row"><input type="text" id="pbwords" value="${esc(S.words)}" maxlength="60" placeholder="${ta('e.g. NO STUDIO')}" style="width:260px"><span class="small" id="pbwn"></span></div>
        ${concept.length ? `<label></label><div class="row small">${t('Your ideas: {list}', {list: concept.map(c => `<button class="fchip sm" data-w="${esc(c.words || '')}" title="${esc(c.sketch || '')}">${esc(c.id)}: ${esc(c.words || '')}</button>`).join('')})}</div>` : ''}
        ${(I.styles || []).length ? `<label>${t('In the style of')}</label><div class="seg" id="pbsty"><button data-v="">${t('no set')}</button>${I.styles.map(s => `<button data-v="${esc(s.name)}" title="${esc(s.font ? tn(s.count, 'the patterns Claude found in {n} thumbnails: the design, the colours, the font - {font} ({how})', 'the patterns Claude found in {n} thumbnails: the design, the colours, the font - {font} ({how})', {font: s.font.family, how: s.font.from === 'measured' ? t('measured|font') : t("Claude's pick")})
          : tn(s.count, 'the patterns Claude found in {n} thumbnails: the design, the colours, the font', 'the patterns Claude found in {n} thumbnails: the design, the colours, the font'))}">${esc(s.label)}</button>`).join('')}</div>` : ''}
        <label>${t('Design')}</label><div class="seg" id="pbtpl">${S.style ? `<button data-v="" title="${ta("the design the set's structure fits")}">${t("the set's")}</button>` : ''}${(I.templates.length ? I.templates : [{name: 'outline'}]).map(d => `<button data-v="${esc(d.name)}" title="${ta(d.what || '')}">${esc(d.name)}</button>`).join('')}</div>
        <label>${t('Thumbnail')}</label><div class="row"><div class="seg" id="pbid">${['A', 'B', 'C'].map(x => `<button data-v="${x}">${x}</button>`).join('')}</div><span class="small muted" id="pbidh"></span></div></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="pbmake">${t('Make it')}</button><span class="small muted" id="pbpick"></span></div></details></div>
    <div class="panel pbsec" id="pb-desc"><div class="row sp"><h2>${t('Description')}</h2><span class="row" style="gap:6px">${desc.text ? `<button class="btn sm" data-cp="desc"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy the description')}</button>` : ''}${tags.line ? `<button class="btn sm" data-cp="tags"><svg class="i"><use href="#i-clipboard"/></svg>${t('Copy the hashtags')}</button>` : ''}</span></div>
      <label class="small muted">${t('Your words (the chapters and hashtags are added under them)')}</label>
      <textarea id="pbbody" rows="4" style="width:100%" placeholder="${ta('what the video is, in two or three lines')}">${esc(desc.body || '')}</textarea>
      <div class="row sp" style="margin-top:10px"><b>${t('Chapters')}</b><span class="row" style="gap:6px"><span class="small muted">${t('suggest from')}</span><button class="btn sm" data-sug="plan" ${I.plan ? '' : `disabled title="${ta('no edit yet')}"`}>${t('the edit')}</button><button class="btn sm" data-sug="transcript">${t('what is said')}</button></span></div>
      <div class="small muted">${I.frames ? t("YouTube wants the first at 0:00, at least three, each 10 seconds or longer. The frame is the finished video's, f0–{last} at {fps} fps.", {last: I.frames - 1, fps})
        : t("YouTube wants the first at 0:00, at least three, each 10 seconds or longer. The frame is the finished video's.")}</div>
      <table class="t pbch"><thead><tr><th>YouTube</th><th>${t('Frame')}</th><th>${t('Timecode')}</th><th>${t('Name')}</th><th></th></tr></thead><tbody id="pbchs"></tbody></table>
      <button class="btn sm ghost" id="pbadd">${t('+ Add a chapter')}</button>
      <div class="nedet spf" style="margin-top:10px"><label>${t('Hashtags')}</label><input type="text" id="pbtags" value="${esc(tags.line || '')}" placeholder="${ta('#music #filmmaking - the first three show by the title')}" style="max-width:560px"></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="pbsave">${t('Save the description')}</button><span class="small muted">${desc.updated ? t('saved {date}', {date: esc(String(desc.updated).replace('T', ' ').slice(0, 16))}) : ''}</span></div>
      <ul class="cklist" id="pbchecks">${(desc.checks || []).filter(c => c.status !== 'PASS').map(c => `<li><b class="${(CK[c.status] || [])[1]}">${(CK[c.status] || ['•'])[0]}</b><span><b>${esc(t(c.part ?? ''))}</b>: ${esc(t(c.rule ?? ''))} <span class="muted">${esc(t(c.detail ?? ''))}</span></span></li>`).join('')}</ul></div>
    ${packagingBox(P)}`;
  wirePackaging(el, P);
  // ---- title
  const own = $('#pbown', el), ownN = $('#pbownn', el);
  own.oninput = () => { ownN.innerHTML = own.value.trim() ? tchars(own.value.trim().length) : ''; };
  const saveTitle = async (text, from = '') => {
    try { const r = await api(url, {title: text, titles_from: (pk.titles || []).length ? '' : from});
      if (!r.ok) { toast(r.checks.filter(c => c.status === 'FAIL').map(c => `${t(c.rule)}: ${t(c.detail)}`).join(' · '), 'err'); return; }
      toast(t('Title saved'), 'ok'); projPublish(el, P); }
    catch (e) { toast(e.message, 'err'); }
  };
  $$('[data-pick]', el).forEach(b => b.onclick = () => { const c = choices[+b.dataset.pick]; saveTitle(c.text, c.from && /^title-/.test(c.from) ? c.from : ''); });
  $('#pbownok', el).onclick = () => { const v = own.value.trim(); if (!v) { own.focus(); return; } saveTitle(v, (I.records[0] || {}).id || ''); };
  $$('[data-cp]', el).forEach(b => b.onclick = () => copy(b.dataset.cp === 'title' ? title : b.dataset.cp === 'desc' ? desc.text : tags.line));
  // ---- thumbnails
  const chk = $('#pbcheck', el); if (chk) chk.onclick = () => runJob('thumb_check', {title});
  $$('.pbthumb', el).forEach(card => {
    const tm = th.find(x => x.id === card.dataset.t);
    $$('[data-lb]', card).forEach(img => img.onclick = () => {
      const L = th.flatMap(x => [['16x9', 'YouTube 16:9'], ['9x16', t('cover 9:16')], ['9x16_crops', t('how the apps crop the cover')]].filter(([k]) => x.files[k]).map(([k, l]) => ({src: x.files[k], cap: `${x.id} · ${l}`})));
      lightbox(L, Math.max(0, L.findIndex(x => x.src === tm.files[img.dataset.lb])));
    });
    $('[data-trender]', card).onclick = () => runJob('thumb_render', {id: tm.id});
    const ts = $('[data-tset]', card);
    if (ts) ts.onclick = () => modal(`<h2>${t('Thumbnail {id}: {words}', {id: esc(tm.id), words: esc(tm.words || '')})}</h2>
      <div class="small muted" style="margin-top:-4px">${t('Change the words, colours, size or where the photo sits, then render it again (about 15 seconds).')}</div>
      <div class="gset" style="margin-top:12px">${tm.settings.map(s => `<label title="${esc(s.id)}">${esc(s.label ? t(s.label) : s.id)}</label><div>${gsetInput(s)}</div>`).join('')}</div>
      <div class="row" style="margin-top:14px"><button class="btn pri" id="tsgo">${t('Save and render again')}</button><button class="btn" id="tsno">${t('Cancel')}</button></div>`, m => {
      $('#tsno', m).onclick = closeModal;
      $('#tsgo', m).onclick = async () => {
        const values = {}; $$('[data-set]', m).forEach(i => { values[i.dataset.set] = gsetValue(i); });
        try { await api(`/api/project/${encodeURIComponent(P.name)}/thumb`, {id: tm.id, values}); closeModal(); runJob('thumb_render', {id: tm.id}); }
        catch (e) { toast(e.message, 'err'); }
      };
    });
  });
  // ---- do it yourself
  const fb = $('#pbfrom', el);
  if (fb) { const paint = () => $$('button', fb).forEach(x => x.classList.toggle('on', x.dataset.v === S.from)); $$('button', fb).forEach(x => x.onclick = () => { S.from = x.dataset.v; paint(); }); paint(); }
  $('#pbcand', el).onclick = () => runJob('thumb_candidates', {render: !!fb && S.from === 'render'});
  $('#pbai', el).onclick = e => { e.preventDefault(); aiPromptsModal('image'); };
  const pickLine = () => {
    const c = S.pick && S.pick.c && items.find(x => x.id === S.pick.c);
    $('#pbpick', el).innerHTML = c ? t('from {clip} {frame} · about 15 seconds', {clip: esc(c.clip), frame: ftc(c.frame, c.fps)}) : S.pick && S.pick.image ? t('from your picture · about 15 seconds') : t('pick a moment or a picture first');
    const n = $('#pbwords', el).value.trim().split(/\s+/).filter(Boolean).length;
    $('#pbwn', el).innerHTML = !n ? '' : n >= 2 && n <= 4 ? `<span class="ok">${t('{n} words ✓', {n})}</span>` : `<span class="amber">${tn(n, '{n} word - 2-4 read best on a phone', '{n} words - 2-4 read best on a phone')}</span>`;
    $('#pbidh', el).textContent = th.some(y => y.id === S.id) ? t('replaces thumbnail {id}', {id: S.id}) : '';
    $('#pbmake', el).textContent = t('Make thumbnail {id}', {id: S.id});
  };
  $$('.pbtile', el).forEach(b => b.onclick = () => {
    S.pick = b.dataset.c ? {c: b.dataset.c} : {image: b.dataset.img};
    $$('.pbtile', el).forEach(x => x.classList.toggle('on', x === b)); pickLine();
  });
  $('#pbwords', el).oninput = e => { S.words = e.target.value; pickLine(); };
  $$('[data-w]', el).forEach(b => b.onclick = () => { $('#pbwords', el).value = S.words = b.dataset.w; pickLine(); });
  const seg = (id, key) => { const b = $(id, el); const paint = () => $$('button', b).forEach(x => x.classList.toggle('on', x.dataset.v === S[key]));
    $$('button', b).forEach(x => x.onclick = () => { S[key] = x.dataset.v; paint(); pickLine(); }); paint(); };
  seg('#pbtpl', 'template'); seg('#pbid', 'id');
  const sty = $('#pbsty', el);                        // 0.4.5: a thumbnail set's style -> the set's design by default
  if (sty) { const paint = () => $$('button', sty).forEach(x => x.classList.toggle('on', x.dataset.v === (S.style || '')));
    $$('button', sty).forEach(x => x.onclick = () => { S.style = x.dataset.v; S.template = S.style ? '' : 'outline'; projPublish(el, P); });
    paint(); }
  pickLine();
  $('#pbimg', el).onchange = async e => {
    const f = e.target.files[0]; e.target.value = '';
    if (!f) return;
    if (f.size > 30e6) { toast(t('Pictures up to 30 MB'), 'err'); return; }
    try { const r = await api(`/api/project/${encodeURIComponent(P.name)}/publish/image`, {name: f.name, data: b64(await f.arrayBuffer())});
      S.pick = {image: r.path}; toast(t('Picture added - type the words and make it'), 'ok'); projPublish(el, P); }
    catch (err) { toast(err.message, 'err'); }
  };
  $('#pbmake', el).onclick = () => {
    const words = $('#pbwords', el).value.trim();
    if (!S.pick) { toast(t('Pick a moment or a picture first'), 'err'); return; }
    if (!words) { $('#pbwords', el).focus(); toast(t('Type the 2-4 words for the thumbnail'), 'err'); return; }
    const c = S.pick.c && items.find(x => x.id === S.pick.c);
    runJob('thumb_make', {id: S.id, words, template: S.template, ...(S.style ? {style: S.style} : {}), ...(c ? {frame: c.frame, clip: c.clip} : {image: S.pick.image})});
  };
  // ---- description: chapters (YouTube time + frame + timecode), hashtags, the words
  let rows = chs.slice();
  const tb = $('#pbchs', el);
  const drawRows = (hints = {}) => {
    tb.innerHTML = rows.map((c, i) => `<tr data-i="${i}"><td class="mono">${ytOf(c.f, fps)}</td>
      <td><input type="number" class="chf" min="0" value="${c.f}" style="width:90px"></td><td class="tc">${tc(c.f, fps)}</td>
      <td><input type="text" class="chn" value="${esc(c.name)}" placeholder="${esc(hints[c.f] || t('a name'))}" style="width:100%"></td>
      <td><button class="btn sm ghost" data-chdel title="${ta('Remove this chapter')}">✕</button></td></tr>`).join('')
      || `<tr><td colspan="5" class="muted small">${t('No chapters - suggest them from the edit, or add them.')}</td></tr>`;
    $$('tr[data-i]', tb).forEach(tr => {
      const i = +tr.dataset.i;
      $('.chf', tr).oninput = e => { rows[i].f = Math.max(0, parseInt(e.target.value, 10) || 0); tr.cells[0].textContent = ytOf(rows[i].f, fps); tr.cells[2].textContent = tc(rows[i].f, fps); };
      $('.chn', tr).oninput = e => { rows[i].name = e.target.value; };
      $('[data-chdel]', tr).onclick = () => { rows.splice(i, 1); drawRows(hints); };
    });
  };
  drawRows();
  $('#pbadd', el).onclick = () => { const last = rows.length ? rows[rows.length - 1].f : -Math.round(10 * fps); rows.push({f: last + Math.round(10 * fps), name: ''}); drawRows(); };
  $$('[data-sug]', el).forEach(b => b.onclick = async () => {
    try {
      const C = await api(`/api/project/${encodeURIComponent(P.name)}/chapters?from=${b.dataset.sug}`);
      const hints = Object.fromEntries(C.points.map(x => [x.f, x.hint || '']));
      const old = Object.fromEntries(rows.map(r => [r.f, r.name]));
      rows = (C.suggested || []).map(f => ({f, name: old[f] || ''}));
      drawRows(hints);
      toast(tn(rows.length, '{n} chapter suggested - name each one, then save', '{n} chapters suggested - name each one, then save') + ((C.warnings || []).length ? ' · ' + C.warnings.join(' ') : ''), 'ok');
    } catch (e) { toast(e.message, 'err'); }
  });
  $('#pbsave', el).onclick = async () => {
    if (!title) { toast(t('Pick or type the title first (above)'), 'err'); own.focus(); return; }
    rows.sort((a, b) => a.f - b.f);
    try {
      const r = await api(url, {title, body: $('#pbbody', el).value, hashtags: $('#pbtags', el).value, chapters: rows.map(c => [c.f, c.name.trim()])});
      if (!r.ok) {
        $('#pbchecks', el).innerHTML = r.checks.filter(c => c.status !== 'PASS').map(c => `<li><b class="${(CK[c.status] || [])[1]}">${(CK[c.status] || ['•'])[0]}</b><span><b>${esc(t(c.part ?? ''))}</b>: ${esc(t(c.rule ?? ''))} <span class="muted">${esc(t(c.detail ?? ''))}</span></span></li>`).join('');
        toast(t('Not saved - fix what is marked ✗ below'), 'err'); return;
      }
      toast(t('Description saved'), 'ok'); projPublish(el, P);
    } catch (e) { toast(e.message, 'err'); }
  };
  reIndex(P, I);
  return I;
}

// ---- Videos > Graphics (0.3.2): the video's HTML graphics (tools\overlay.py): settings, render, save to the library
// 0.4.6: the font library (the lab's fonts folder) - a font setting lists every bundled family by what it suits, the
// Windows fonts older graphics used after them, and shows the picked one in a preview line (/fonts.css loads a family
// only when something shows it)
let FONTS = null;
const FONT_GROUPS = {yours: t('Your fonts (this PC only)'), 'heavy condensed': t('Heavy and narrow'), 'heavy wide': t('Heavy and wide'), 'friendly / rounded': t('Friendly, rounded'),
  'playful display': t('Playful'), 'handwritten / marker': t('Handwritten'), 'serif display': t('Serif'), 'clean text': t('Clean text'),
  'tech / mono': t('Tech'), other: t('Other|font group')};
const isFontSet = s => s.type === 'enum' && (s.id === 'font' || /_font$/.test(s.id));
const fontCss = f => `font-family:'${String(f).replace(/['"\\<>]/g, '')}', sans-serif`;
function fontOptions(s) {
  const v = s.value, opt = (val, label, tip) => `<option value="${esc(val)}" ${val === v ? 'selected' : ''} style="${fontCss(val)}"${tip ? ` title="${esc(tip)}"` : ''}>${esc(label)}</option>`;
  const declared = (s.options || []).map(o => o.value);
  if (!FONTS) return (s.options || []).map(o => opt(o.value, t(o.label ?? ''))).join('');
  const groups = {};
  FONTS.families.forEach(f => { (groups[f.group] = groups[f.group] || []).push(f); });
  const known = new Set([...FONTS.families.map(f => f.family), ...FONTS.windows]);
  const extra = declared.filter(x => !known.has(x));
  // My Brand's fonts first (step 3, 2026-10-26): its titles and body text fonts, when they are in the library
  if (BRAND_DATA === null) brandData();
  const bf = (((BRAND_DATA || {}).identity || {}).fonts) || {};
  const mineF = [[bf.heading, t('your brand font for titles')], [bf.body, t('your brand font for body text')]]
    .filter(([f], i, a) => f && known.has(f) && a.findIndex(([g]) => g === f) === i);
  return (mineF.length ? `<optgroup label="${ta('My Brand')}">${mineF.map(([f, tip]) => opt(f, f, tip)).join('')}</optgroup>` : '')
    + Object.entries(groups).map(([g, L]) => `<optgroup label="${esc(FONT_GROUPS[g] || g)}">${L.map(f => opt(f.family, f.family, f.own ? t('your own font - on this PC only') : t('free font ({licence}), comes with MotionLab', {licence: f.licence}))).join('')}</optgroup>`).join('')
    + `<optgroup label="${ta('Windows only (another PC may draw them differently)')}">${FONTS.windows.map(w => opt(w, w)).join('')}</optgroup>`
    + (extra.length ? `<optgroup label="${ta('In this graphic')}">${extra.map(x => opt(x, x)).join('')}</optgroup>` : '');
}
const fontPreview = v => `<div class="fprev" style="${fontCss(v)}" title="${ta('how this font looks')}">${t('Aa Bb 0123 - the quick brown fox')}</div>`;
document.addEventListener('change', e => {
  const tg = e.target;
  if (tg.matches && tg.matches('select[data-font]') && tg.nextElementSibling && tg.nextElementSibling.classList.contains('fprev')) tg.nextElementSibling.style.cssText = fontCss(tg.value);
});

// the logo library (logos\, tools\logos.py, 2026-10-16): a logo setting (id logo / logos / *_logo / *_logos) gets *Pick a
// logo…*, a text setting whose label shows ":name:" gets *+ Logo* (it writes ":youtube:"); both open the picker under the
// field (not a dialog: the template's own dialog keeps its values). The live previews load the logos the values name.
let LOGOS = null;
const LOGO_GROUPS = {brand: t('My Brand'), social: t('Social & video'), ai: t('AI tools'), creative: t('Creative apps'), dev: t('Code'), work: t('Work & money'), web: t('Browsers & systems'), other: t('Other|logo group')};
const LOGO_STYLES = [['', t('Auto - fits the background')], ['color', t('In its colours')], ['mono', t('One colour')], ['wordmark', t('The name written out')]];
const LOGO_VARIANT = {color: t('its colours'), mono: t('one colour - takes any colour'), wordmark: t('the name written out'), 'color-dark': t('its colours, for a dark background'), 'wordmark-dark': t('the name, for a dark background')};
const isLogoSet = s => s.type === 'string' && (/^logos?$/.test(s.id) || /_logos?$/.test(s.id));
const logoText = s => s.type === 'string' && !isLogoSet(s) && /:[a-z][a-z0-9-]*:/.test(s.label || '');
const logoSrc = (lg, v) => { const k = v && lg.variants[v] ? v : lg.default;       // My Brand's logo: its own picture (src)
  return fileUrl(lg.variants[k].src || `logos/${lg.id}/${k}.svg`); };
const logoLoad = () => LOGOS ? Promise.resolve(LOGOS) : api('/api/logos').then(d => (LOGOS = d));
const logoFind = (L, q) => { const w = q.toLowerCase().split(/\s+/).filter(Boolean);
  return L.filter(lg => w.every(x => `${lg.id} ${lg.name.toLowerCase()} ${lg.words.join(' ')} ${lg.group}`.includes(x))); };
const logoTile = (lg, v, cls = '') => { const k = v && lg.variants[v] ? v : lg.default;
  return `<span class="lgimg${lg.variants[k].on === 'dark' ? ' dk' : ''} ${cls}"><img src="${logoSrc(lg, k)}" alt="" loading="lazy"></span>`; };
// the logo names in a graphic's values - a live preview loads just those ("a|b/mono" in a logo setting, ":a:" in a text)
function logoIds(vals) {
  const ids = new Set();
  Object.values(vals || {}).forEach(v => {
    if (typeof v !== 'string') return;
    v.split('|').forEach(x => { const m = /^\s*:?([a-z0-9][a-z0-9-]*)(?:\/[a-z0-9-]+)?:?\s*$/i.exec(x); if (m) ids.add(m[1].toLowerCase()); });
    for (const m of v.matchAll(/:([a-z0-9][a-z0-9-]*)(?:\/[a-z0-9-]+)?:/gi)) ids.add(m[1].toLowerCase());
  });
  return [...ids].slice(0, 200);
}
document.addEventListener('click', e => {
  const b = e.target.closest && e.target.closest('[data-logopick]');
  if (!b) return;
  e.preventDefault();
  const host = b.closest('.lgin'), inp = $('input[data-set]', host), was = host._pop && host._pop.isConnected;
  $$('.lgpop').forEach(x => x.remove());
  if (!was) logoPicker(host, inp, b.dataset.logopick);
});
['keyup', 'click', 'focus'].forEach(ev => document.addEventListener(ev, e => {            // where a text's logo goes
  const t = e.target;
  if (t && t.matches && t.matches('input[data-logohow]')) t.dataset.caret = t.selectionStart ?? '';
}, true));
async function logoPicker(host, inp, mode) {
  const pop = document.createElement('div');
  pop.className = 'lgpop';
  pop.innerHTML = `<div class="small muted">${t('Loading the logos…')}</div>`;
  const cell = host.parentElement;                 // in a settings form: a row of its own, as wide as the form
  (cell && cell.parentElement && cell.parentElement.classList.contains('gset') ? cell : host).after(pop);
  host._pop = pop;
  let D;
  try { D = await logoLoad(); } catch (e) { pop.innerHTML = `<div class="small bad">${esc(e.message)}</div>`; return; }
  let q = '', g = '', st = '';
  pop.innerHTML = `<div class="row" style="gap:6px"><input type="search" class="lgq" placeholder="${ta('Search: youtube, editing, ai…')}" style="flex:1;min-width:0">
      <select class="lgst" title="${ta('Which version')}">${LOGO_STYLES.map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join('')}</select>
      <button type="button" class="btn sm lgx" title="${ta('Close')}">✕</button></div>
    <div class="row lgg">${[['', t('All|logos')], ...Object.keys(D.groups || {}).map(k => [k, LOGO_GROUPS[k] || k])].map(([k, l]) => `<button type="button" class="fchip sm${k ? '' : ' on'}" data-g="${esc(k)}">${esc(l)}</button>`).join('')}</div>
    <div class="lggrid"></div>
    <div class="small dim">${mode === 'many' ? t('Click several: each one joins the list.') : mode === 'text' ? t('It goes in written like :youtube: - the graphic draws the logo there.') : t('A click puts it in.')} ${t('Logos are trademarks of their owners: use them to name the products your video is about.')}</div>`;
  const grid = $('.lggrid', pop);
  const draw = () => {
    const L = logoFind(D.logos.filter(lg => !g || lg.group === g), q);
    grid.innerHTML = L.map(lg => { const has = !st || lg.variants[st];
      return `<button type="button" class="lgb${has ? '' : ' off'}" data-lg="${esc(lg.id)}" title="${has ? esc(lg.name) : ta('{name} - it has no such version: the usual one', {name: lg.name})}">${logoTile(lg, has ? st : '')}<span>${esc(lg.name)}</span></button>`; }).join('')
      || `<div class="small muted">${t('No logo fits those words.')}</div>`;
  };
  draw();
  const qi = $('.lgq', pop);
  qi.oninput = () => { q = qi.value; draw(); };
  $('.lgst', pop).onchange = e => { st = e.target.value; draw(); };
  $('.lgx', pop).onclick = () => pop.remove();
  $$('[data-g]', pop).forEach(b => b.onclick = () => { g = b.dataset.g; $$('[data-g]', pop).forEach(x => x.classList.toggle('on', x === b)); draw(); });
  grid.onclick = e => {
    const b = e.target.closest('[data-lg]');
    if (!b) return;
    const lg = D.logos.find(x => x.id === b.dataset.lg), val = st && lg.variants[st] ? `${lg.id}/${st}` : lg.id;
    if (mode === 'one') inp.value = val;
    else if (mode === 'many') { const L = inp.value.split('|').map(x => x.trim()).filter(Boolean); if (!L.includes(val)) L.push(val); inp.value = L.join('|'); }
    else {
      const tok = `:${val}:`, v = inp.value, how = inp.dataset.logohow, c = inp.dataset.caret === undefined || inp.dataset.caret === '' ? null : Number(inp.dataset.caret);
      if (how === 'swap' && (v.trim().length <= 3 || /^\s*:[a-z0-9/-]+:\s*$/i.test(v))) inp.value = tok;     // letters / an emoji / a logo -> this logo
      else if (how === 'first' && c == null) inp.value = tok + ' ' + v.replace(/^\s*:[a-z0-9/-]+:\s*/i, '');
      else if (c == null) inp.value = v ? `${v}${how === 'list' ? '|' : ' '}${tok}` : tok;
      else { const a = v.slice(0, c), z = v.slice(c);
        inp.value = a + (a && !/[\s|]$/.test(a) ? ' ' : '') + tok + (z && !/^[\s|:]/.test(z) ? ' ' : '') + z; }
      inp.dataset.caret = '';
    }
    inp.dispatchEvent(new Event('input', {bubbles: true}));
    inp.dispatchEvent(new Event('change', {bubbles: true}));
    if (mode !== 'many') pop.remove();
  };
  qi.focus();
}

function gsetInput(s) {
  const a = `data-set="${esc(s.id)}" data-type="${esc(s.type)}"`, v = s.value;
  if (isFontSet(s)) return `<select ${a} data-font>${fontOptions(s)}</select>${fontPreview(v)}`;
  if (isLogoSet(s)) return `<div class="lgin"><input type="text" ${a} value="${esc(v)}" placeholder="youtube, figma/mono…"><button type="button" class="btn sm" data-logopick="${/s$/.test(s.id) ? 'many' : 'one'}">${t('Pick a logo…')}</button></div>`;
  if (logoText(s)) return `<div class="lgin"><input type="text" ${a} value="${esc(v)}" data-logohow="${/\| between/.test(s.label) ? 'list' : /first/.test(s.label) ? 'first' : 'swap'}"><button type="button" class="btn sm" data-logopick="text" title="${ta('Put a logo of the library in this text')}">${t('+ Logo')}</button></div>`;
  if (s.type === 'color') return `<input type="color" ${a} value="${esc(v)}">`;
  if (s.type === 'boolean') return `<input type="checkbox" ${a} ${v ? 'checked' : ''}>`;
  // an option's label = the template's own words (overlay.json / index.html, English): shown in Spanish by key (_by_key)
  if (s.type === 'enum') return `<select ${a}>${(s.options || []).map(o => `<option value="${esc(o.value)}" ${o.value === v ? 'selected' : ''}>${esc(t(o.label ?? ''))}</option>`).join('')}</select>`;
  if (s.type === 'number') return `<input type="number" ${a} value="${esc(v)}"${s.min != null ? ` min="${s.min}"` : ''}${s.max != null ? ` max="${s.max}"` : ''} step="${s.step ?? 'any'}">`;
  return `<input type="text" ${a} value="${esc(v)}">`;
}
const gsetValue = i => i.dataset.type === 'boolean' ? i.checked : i.dataset.type === 'number' ? Number(i.value) : i.value;

// 0.4.6: a graphic drawn live in the page - its own HTML + GSAP in a frame, the settings as they are in the form (no
// HyperFrames, no render, no Claude): a change shows at once; the slider and ▶ move through its frames. The rendered
// picture stays the fallback when the graphic does not run here (no window.__timelines.main).
function livePreview(box, o, getValues) {
  const W = o.width || 1920, H = o.height || 1080, fps = o.fps || 25, N = Math.max(1, o.frames || 1);
  const sc = Math.min((box.clientWidth || 300) / W, 560 / H);
  const base = '/files/' + String(o.folder).replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/') + '/';
  box.innerHTML = `<div class="glv" style="width:${Math.round(W * sc)}px;height:${Math.round(H * sc)}px"><iframe title="${ta('live preview')}" style="width:${W}px;height:${H}px;transform:scale(${sc})"></iframe></div>
    <div class="glvbar"><button class="btn sm" data-lvp title="${ta('play / pause')}">▶</button><input type="range" min="0" max="${N - 1}" value="0" data-lvr><span class="small mono" data-lvf></span></div>
    <div class="small muted">${t('Live preview: a change shows here at once, before you save or render.')}</div>`;
  const fr = $('iframe', box), rng = $('[data-lvr]', box), lab = $('[data-lvf]', box), play = $('[data-lvp]', box);
  let html = null, f = null, tl = null, raf = 0, t0 = 0, f0 = 0, timer = 0;
  const show = () => { lab.innerHTML = ftc(f, fps); rng.value = f; if (tl) try { tl.seek(f / fps, false); } catch (e) { /* the graphic's own error */ } };
  const stop = () => { cancelAnimationFrame(raf); raf = 0; play.textContent = '▶'; };
  const fail = () => { stop(); box.innerHTML = gthumb(o) + `<div class="small muted">${t('No live preview for this graphic - render it to see a change.')}</div>`; };
  fr.onload = () => {
    const w = fr.contentWindow;
    let tries = 0;
    const ready = () => {
      tl = w && w.__timelines && w.__timelines.main;
      // a look-aware template registers its timeline once its fonts are in (after load): wait up to 3 s for it
      if (!tl) return ++tries < 30 ? setTimeout(ready, 100) : fail();
      if (f == null) {                            // start where something shows: the first caption, else a third in
        const cue = w.CAPTIONS && w.CAPTIONS.cues && w.CAPTIONS.cues[0];
        f = cue ? Math.min(N - 1, Math.round((cue.f0 + cue.f1) / 2)) : Math.floor(N * 0.3);
      }
      show();
      if (w.document.fonts) w.document.fonts.ready.then(show);
    };
    ready();
  };
  const load = async () => {
    try { html = html || await (await fetch(base + 'index.html', {cache: 'no-store'})).text(); } catch (e) { return fail(); }
    const V0 = getValues(), vals = JSON.stringify(V0).replace(/</g, '\\u003c'), lgs = encodeURIComponent(logoIds(V0).join(','));
    fr.srcdoc = html.replace(/<head[^>]*>/i, m => `${m}<base href="${base}"><link rel="stylesheet" href="/fonts.css"><script src="/logos.js?b=${lgs}"><\/script><script>window.__hyperframes = {getVariables: () => (${vals})};<\/script>`);
  };
  rng.oninput = () => { stop(); f = Number(rng.value); show(); };
  play.onclick = () => {
    if (raf) return stop();
    if (f >= N - 1) f = 0;
    play.textContent = '❚❚'; t0 = performance.now(); f0 = f;
    const step = now => { f = Math.min(N - 1, f0 + Math.floor((now - t0) / 1000 * fps)); show(); if (f < N - 1) raf = requestAnimationFrame(step); else stop(); };
    raf = requestAnimationFrame(step);
  };
  load();
  return {refresh: () => { clearTimeout(timer); timer = setTimeout(load, 120); }, stop};
}

// 0.4.6: a graphic's ready-made looks (Classic | Clean box ...): one click sets them; captions made before their
// example had looks take its newest design first (the words and settings stay)
const lookRow = o => {
  const L = (o.looks || {}).looks || {}, ids = Object.keys(L);
  if (!ids.length) return '';
  const on = ids.find(k => L[k].active);
  return `<div class="glooks"><span class="small muted">${t('Look')}</span><div class="seg">${ids.map(k => `<button data-look="${esc(k)}" class="${k === on ? 'on' : ''}" title="${esc(t(L[k].what || ''))}">${esc(t(L[k].label ?? ''))}</button>`).join('')}</div>
    <span class="small muted">${o.looks.upgrade ? t('picking one also brings these captions to the newest design - your words and settings stay') : on ? '' : t('your own settings')}</span></div>`;
};
const gthumb = g => g.thumb ? `<img src="${fileUrl(g.thumb)}?v=${g.thumb_v}" alt="" loading="lazy">` : `<div class="muted small">${t('no picture yet')}</div>`;

function projGraphics(el, P) {
  const O = P.overlays || [];
  const top = `<div class="row sp" style="margin-bottom:12px"><div class="hint">${t('Titles, clocks, captions and other graphics, rendered as see-through clips for your video and for DaVinci Resolve. Change a setting, Save, then Render - it renders on this PC, no Claude and no tokens; the picture shows the result when it is done.')}</div>
    <button class="btn sm" id="gcap">${t('Captions…')}</button></div>`;
  if (!O.length) {
    el.innerHTML = top + `<div class="empty">${t('No graphics in this video yet. Make captions from a subtitle file, or ask Claude for a new one when you recreate a video.')}</div>`;
    captionsBtn(el, P);
    return;
  }
  // where the captions' words came from, as captions.load names it in overlay.json: "SRT file" / "VTT file" (by key)
  // or "lab transcript (<source>, <kind>)"
  const capWhat = w => { const m = /^lab transcript \((.*)\)$/.exec(w || ''); return m ? t('lab transcript ({how})', {how: m[1]}) : t(w || ''); };
  el.innerHTML = top + `
    <div class="col">${O.map(o => {
      const st = o.current ? `<span class="ok">${t('rendered ✓')}</span> <span class="muted">${esc(o.rendered_at)}</span>`
        : o.rendered ? `<span class="amber">${t('settings changed: render it again')}</span>` : `<span class="amber">${t('not rendered yet')}</span>`;
      return `<div class="gcard" data-g="${esc(o.name)}"><div class="gside"><div class="gthumb">${gthumb(o)}</div></div>
        <div><div class="row sp"><b style="font-size:15px">${esc(o.name)}</b><span class="small muted">${t('{frames} frames {range} · {width}×{height} · {fps} fps', {frames: o.frames, range: frange(0, o.frames - 1, o.fps), width: o.width, height: o.height, fps: o.fps})}</span></div>
          <div class="small" style="margin:4px 0 10px">${st} · ${o.used_in.length ? t('in the edit: {versions}', {versions: o.used_in.map(esc).join(', ')}) : `<span class="muted">${t('not in an edit version yet')}</span>`}</div>
          ${o.captions ? `<div class="small" style="margin:-4px 0 10px">${t('Captions: {lines}, {words} from the {what}', {lines: plural(o.captions.cues, 'line'), words: plural(o.captions.words, 'word'), what: esc(capWhat(o.captions.what))})}${o.captions.estimated ? ` · <span class="amber">${t('word times estimated (the file has one time per line)')}</span>` : ''}</div>` : ''}
          ${o.problem ? `<div class="bad small">${esc(o.problem)}</div>` : ''}
          ${lookRow(o)}
          ${o.settings.length ? `<div class="gset">${o.settings.map(s => `<label title="${esc(s.id)}">${esc(t(s.label || s.id || ''))}</label><div>${gsetInput(s)}</div>`).join('')}</div>`
            : `<div class="muted small">${t('This graphic has no settings yet (Claude can add them: text, colours, timing).')}</div>`}
          <div class="row" style="margin-top:10px">${o.settings.length ? `<button class="btn sm" data-gsave disabled>${t('Save settings')}</button>` : ''}
            <button class="btn sm ${o.current ? '' : 'pri'}" data-grender>${t('Render')}</button>
            <button class="btn sm" data-glib ${o.current ? '' : `disabled title="${ta('render it first')}"`}>${t('Save to library…')}</button>
            ${o.srt ? `<button class="btn sm" data-open="${esc(o.srt)}" data-reveal title="${ta("the same captions as subtitles: import it into DaVinci Resolve's subtitle track and correct them there")}">${t('Subtitles for Resolve (.srt)')}</button>` : ''}
            <button class="btn sm" data-open="${esc(o.folder)}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>
          <div class="row" style="margin-top:8px"><span class="small muted">DaVinci Resolve:</span>
            <button class="btn sm" data-gclip ${o.rendered ? '' : 'disabled'} title="${ta("a numbered copy of this render to drag into Resolve's media pool - Resolve locks the files it uses, so the graphic itself stays free to render again")}">${t('Clip for Resolve (.mov)')}</button>
            <button class="btn sm" data-gswap ${o.rendered ? '' : 'disabled'} title="${ta('after a new render: replaces this graphic in the project open in Resolve - position, length, size, opacity and blend mode on your timeline stay')}">${t('Swap in DaVinci Resolve')}</button></div>
          <pre class="log" hidden></pre></div></div>`;
    }).join('')}</div>`;
  captionsBtn(el, P);
  $$('.gcard', el).forEach(card => {
    const name = card.dataset.g, pre = $('pre.log', card), save = $('[data-gsave]', card);
    const o = O.find(x => x.name === name);
    const formValues = () => { const v = {}; o.settings.forEach(s => { v[s.id] = s.value; }); $$('[data-set]', card).forEach(i => { v[i.dataset.set] = gsetValue(i); }); return v; };
    const live = o.settings.length && !o.problem ? livePreview($('.gside', card), o, formValues) : null;
    if (live) CLEAN.push(live.stop);
    $$('[data-set]', card).forEach(i => { i.oninput = i.onchange = () => { if (save) save.disabled = false; if (live) live.refresh(); }; });
    $$('[data-look]', card).forEach(b => b.onclick = async () => {
      try {
        await api(`/api/project/${encodeURIComponent(P.name)}/overlay`, {overlay: name, preset: b.dataset.look});
        toast(t('{name}: the look “{look}” - render it to use it in the video', {name, look: b.textContent}), 'ok'); route();
      } catch (e) { toast(e.message, 'err'); }
    });
    if (save) save.onclick = async () => {
      const values = {};
      $$('[data-set]', card).forEach(i => { values[i.dataset.set] = gsetValue(i); });
      try { await api(`/api/project/${encodeURIComponent(P.name)}/overlay`, {overlay: name, values}); toast(t('{name}: settings saved - render it to see them', {name}), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
    const run = async (kind, args, btn, then) => {
      if (save && !save.disabled) { toast(t('Save the settings first'), 'err'); return; }
      const j = await startJob(kind, {project: P.name, overlay: name, ...args}, false);
      if (!j) return;
      btn.disabled = true; pre.hidden = false; pre.textContent = '';
      followJob(j.id, pre, jj => {
        toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
        if (jj.status !== 'done') { btn.disabled = false; return; }
        if (then) then(); else route();
      });
    };
    $('[data-grender]', card).onclick = e => run('overlay_render', {}, e.target);
    $('[data-gswap]', card).onclick = e => run('overlay_refresh', {}, e.target, () => { e.target.disabled = false; });
    $('[data-gclip]', card).onclick = e => run('overlay_resolve_clip', {}, e.target, async () => {
      e.target.disabled = false;
      try {
        const NP = await api('/api/project/' + encodeURIComponent(P.name));
        const o2 = (NP.overlays || []).find(x => x.name === name);
        if (o2 && o2.resolve_clips && o2.resolve_clips[0]) openPath(o2.resolve_clips[0], true);
      } catch (err) { toast(err.message, 'err'); }
    });
    $('[data-glib]', card).onclick = e => modal(`<h2>${t('Save “{name}” to the graphics library', {name: esc(name)})}</h2>
      <div class="small muted">${t('The library keeps its HTML, its settings as they are now and the rendered clip. Every video can use it (Library → Graphics), and you can drag the clip into a Power Bin in DaVinci Resolve.')}</div>
      <div class="row" style="margin-top:12px"><label>${t('Name')} <input id="glname" value="${esc(name)}" style="width:220px"></label>
        <label class="chk"><input type="checkbox" id="glrep"> ${t('replace one with that name')}</label></div>
      <div class="row" style="margin-top:12px"><button class="btn pri" id="glgo">${t('Save to library')}</button></div>`, m => {
      $('#glgo', m).onclick = () => { const nm = $('#glname', m).value.trim(), rep = $('#glrep', m).checked; closeModal(); run('overlay_save', {name: nm, replace: rep}, e.target); };
    });
  });
}

function captionsBtn(el, P) {
  // captions from a video's own words (speech to text, faster-whisper) or from a subtitle file (.srt / .vtt)
  const b = $('#gcap', el);
  if (!b) return;
  const SPc = P.speech || {}, media = P.media || [];
  b.onclick = () => modal(`<h2>${t('Captions')}</h2>
    <div class="small muted">${t("Styled captions timed to the words (change the style afterwards on this tab) and the same captions as an .srt for DaVinci Resolve's subtitle track. Your files are only read.")}</div>
    <div class="col" style="margin-top:12px">
      <label class="chk"><input type="radio" name="gcsrc" value="video" ${SPc.available && media.length ? 'checked' : 'disabled'}> ${t('<b>From the words in a video</b> (speech to text, on this PC)')}</label>
      <div class="col" id="gcvid" style="margin-left:24px">${SPc.available ? (media.length ? `
        <label>${t('Video')} <select id="gcm">${media.map(m => `<option value="${esc(m.path)}">${esc(m.label)}</option>`).join('')}</select></label>
        <div class="hint">${t('Pick the render of your edit, so the captions follow its cuts - or one of your clips.')}</div>
        <label>${t('Names and words it might not know')} <input id="gcnames" placeholder="${ta('e.g. MotionLab, 4AM, Nemzzz, DaVinci Resolve')}"></label>
        <label>${t('Model')} <select id="gcmod"><option value="small">${t('small - the most accurate')}</option><option value="base">${t('base - lighter, for slow laptops (ignores the names)')}</option></select></label>`
        : `<div class="hint">${t('This video has no render or clip yet.')}</div>`)
        : `<div class="hint">${t('Speech to text is not installed yet: <a href="#/settings">Settings → Programs → Speech to text → Install</a> (one time, about 520 MB).')}</div>`}</div>
      <label class="chk"><input type="radio" name="gcsrc" value="file" ${SPc.available && media.length ? '' : 'checked'} ${P.plans.length ? '' : 'disabled'}> ${P.plans.length ? t("<b>From a subtitle file</b> (.srt / .vtt from YouTube, CapCut, Resolve's “Create Subtitles from Audio”)")
        : t("<b>From a subtitle file</b> (.srt / .vtt from YouTube, CapCut, Resolve's “Create Subtitles from Audio”) - needs an edit version (its size, rate and length)")}</label>
      <div style="margin-left:24px"><input id="gcf" placeholder="${ta('C:\\...\\my video.srt')}"></div>
      <label>${t('Name')} <input id="gcn" value="captions" style="width:200px"></label>
      <label class="chk" id="gcbrand" hidden><input type="checkbox" checked> ${t('In my brand\'s caption style')}</label></div>
    <div class="hint" style="margin-top:6px">${t('The same name again replaces the words of those captions and keeps their style.')}</div>
    <div class="row" style="margin-top:12px"><button class="btn pri" id="gcgo">${t('Make the captions')}</button><span id="gcmsg" class="small"></span></div><pre class="log" hidden></pre>`, m => {
    brandData().then(b => {                       // 0.6.0: My Brand has a caption style - offered, ticked
      if (Object.values(((b.identity || {}).captions) || {}).some(v => v !== '' && v != null)) $('#gcbrand', m).hidden = false;
      const gn = $('#gcnames', m), words = (b.glossary || []).map(g => g.word);     // its names and words: speech to text
      if (gn && words.length && !gn.value.trim()) gn.value = words.join(', '); });
    $('#gcgo', m).onclick = async () => {
      const go = $('#gcgo', m), src = ($('input[name=gcsrc]:checked', m) || {}).value;
      if (!src) { toast(t('Pick where the words come from'), 'err'); return; }
      const args = {project: P.name, name: $('#gcn', m).value.trim(), brand: !$('#gcbrand', m).hidden && $('#gcbrand input', m).checked};
      if (src === 'video') Object.assign(args, {file: $('#gcm', m).value, names: $('#gcnames', m).value.trim(), model: $('#gcmod', m).value});
      else args.file = $('#gcf', m).value.trim();
      const j = await startJob('overlay_captions', args, false);
      if (!j) return;
      go.disabled = true; const pre = $('pre.log', m); pre.hidden = false;
      followJob(j.id, pre, jj => {
        if (jj.status === 'done') { closeModal(); route(); }
        else { $('#gcmsg', m).innerHTML = `<span class="bad">${t('did not work - see the log')}</span>`; go.disabled = false; }
      });
    };
  });
}

function projTiming(el, P) {
  const what = `<div class="hint" style="margin-bottom:12px">${t('For an exact copy of a reference: does your render change picture on the same frames as the reference - every cut, flash and pop-in Claude picked from it? ✓ = on the same frame, ✗ = missed (Claude fixes those). The small number = how much the picture changed there (0-255).')}</div>`;
  if (!P.verifies.length) { el.innerHTML = what + `<div class="empty">${t('No timing check for this video - Claude makes one when it copies a reference frame by frame.')}</div>`; return; }
  const fps = (P.plans[0] || {}).fps || 25, keys = P.verifies[0].rows;
  el.innerHTML = `${what}<div class="panel"><h2>${t("Does the render change picture on the reference's key frames?")}</h2>
    <div class="row" style="margin-bottom:10px">${P.verifies.map(v => `<div class="stat"><div class="n">${v.hits}<span class="muted" style="font-size:16px"> / ${v.keys}</span></div>
      <div class="l">${t('{name} · brightness correlation {corr}', {name: esc(v.name), corr: numStr(v.luma_corr)})}</div>
      <button class="btn sm" style="margin-top:6px" data-run="${esc(v.name)}">${t('Run again')}</button></div>`).join('')}</div>
    <table class="t"><thead><tr><th>${t('Frame')}</th><th>${t('Timecode')}</th><th>${t('What happens in the reference')}</th>${P.verifies.map(v => `<th>${esc(v.name)}</th>`).join('')}</tr></thead><tbody>
    ${keys.map((k, i) => `<tr><td class="fr">f${k.frame}</td><td class="tc">${tc(k.frame, fps)}</td><td>${esc(k.what)}</td>
      ${P.verifies.map(v => { const r = v.rows[i] || {}; return `<td>${r.our_hit ? `<span class="ok">${t('✓ same frame')}</span>` : `<span class="bad">${t('✗ missed')}</span>`} <span class="small dim">${numStr(r.our_change ?? '')}</span></td>`; }).join('')}</tr>`).join('')}
    </tbody></table></div>`;
  $$('[data-run]', el).forEach(b => b.onclick = () => startJob('verify_timing', {project: P.name, render: b.dataset.run}));
}

function projResolve(el, P) {
  const what = `<div class="hint" style="margin-bottom:12px">${t('The same edit as a DaVinci Resolve project you can keep editing by hand. <b>Check-up</b> = is the timeline still what the lab built; <b>What did I change by hand?</b> = your changes in Resolve, so the next version keeps them; <b>Effects in this rebuild</b> = tick the ones to keep in your library (Claude saves each as a Fusion effect for every later video).')}</div>`;
  if (!P.resolve.length) { el.innerHTML = what + `<div class="empty">${t('No DaVinci Resolve version of this video yet - tick "then build it as a DaVinci Resolve project" in New edit.')}</div>`; return; }
  const fps = (P.plans[0] || {}).fps || 25;
  const render = P.renders.find(r => r.kind === 'resolve') || P.renders[0];
  const picks = Object.assign({}, P.library_picks || {});
  const savePicks = debounce(async () => {
    try { await api(`/api/project/${encodeURIComponent(P.name)}/picks`, {picks}); $('#psaved').textContent = t('saved ✓'); }
    catch (e) { toast(e.message, 'err'); }
  }, 400);
  el.innerHTML = what + P.resolve.map((R, ri) => {
    const d = R.drift, f = d ? d.findings : [];
    const byUnit = {};
    f.forEach(x => (byUnit[x.unit] = byUnit[x.unit] || []).push(x));
    return `<div class="grid g2"><div class="panel"><h2>${t('Timeline')} <span class="amber">${esc(R.timeline)}</span></h2>
      <div class="kv"><b>${t('Project')}</b><span>${esc(R.project)} (Resolve)</span><b>${t('Built from')}</b><span>${t('{units} pieces: {clips} Edit-page clips, {comps} Fusion comps, {luts} grade LUTs, {tracks} video tracks', {units: R.units, clips: R.clips, comps: R.comps, luts: R.luts, tracks: R.tracks})}</span>
        <b>${t('Backup')}</b><span>${R.drp ? `<a href="#" data-open="${esc(R.drp)}" data-reveal>${esc(R.drp.split('/').pop())}</a>` : '–'}</span>
        <b>${t('Report')}</b><span>${R.report ? `<a href="#" class="showrep" data-rep="${esc(R.report)}">${t('option 2 report')}</a>` : '–'}</span></div>
      <div class="row" style="margin-top:12px"><button class="btn" data-job="resolve_doctor">${t('Check-up')}</button>
        <button class="btn" data-job="resolve_diff">${t('What did I change by hand?')}</button><span class="hint">${t('needs Resolve running')}</span></div>
      <pre class="log" id="rlog${ri}" hidden></pre></div>
      <div class="panel"><h2>${t('Changed by hand in Resolve')}</h2>${d ? `<div class="small muted" style="margin-bottom:8px">${t('last checked {when}', {when: esc(d.checked)})}</div>
        ${f.length ? Object.entries(byUnit).map(([u, xs]) => `<div style="margin-bottom:10px"><b class="amber">${esc(u)}</b>
          <span class="small muted">V${xs[0].track} · ${frange(xs[0].start, xs[0].end, fps)}</span>
          <ul class="small" style="margin:4px 0">${xs.map(x => `<li>${esc(x.what)}: <span class="muted">${t('lab')}</span> ${esc(x.lab)} <span class="muted">${t('→ now')}</span> <b>${esc(x.live)}</b></li>`).join('')}</ul></div>`).join('')
          : `<div class="ok">${t('Nothing: the timeline is exactly what the lab built.')}</div>`}
        ${R.edits.length ? `<div class="small muted">${t('Your edited comps are kept as text: {files}', {files: R.edits.map(p => `<a href="#" data-open="${esc(p)}" data-reveal>${esc(p.split('/').pop())}</a>`).join(', ')})}</div>` : ''}`
        : `<div class="muted">${t('Not checked yet: click “What did I change by hand?”.')}</div>`}</div></div>
      <div class="row sp" style="margin:18px 0 8px"><div><h2 style="margin:0">${t('Effects in this rebuild')}</h2>
        <div class="hint">${t('Tick the effects you want saved in your library (a Fusion macro + a recipe each). Claude does the saving in Resolve; this is your list.')}</div></div>
        <span id="psaved" class="small muted">${P.picks_updated ? t('saved {when}', {when: esc(P.picks_updated)}) : ''}</span></div>
      <div class="col">${R.effects.map(g => {
        const u0 = g.units[0], mid = Math.round((u0.start + u0.end) / 2), pk = picks[g.title] || {};
        return `<div class="fx ${pk.pick ? 'picked' : ''}" data-fx="${esc(g.title)}">
          ${render ? `<img loading="lazy" src="/api/thumb?video=${encodeURIComponent(render.rel)}&f=${mid}&fps=${fps}" title="${ta('f{frame} ({tc}) in {render}', {frame: mid, tc: tc(mid, fps), render: render.name})}">` : '<div></div>'}
          <div><div class="row sp"><b style="font-size:15px">${esc(t(g.title))}</b><label class="chk"><input type="checkbox" data-pick ${pk.pick ? 'checked' : ''}> ${t('save to library')}</label></div>
          <div class="small" style="margin:3px 0 6px">${esc(t(g.what || ''))}</div>
          <div class="units">${g.units.map(u => `${esc(u.name)} ${u.track ? `V${u.track}` : ''} ${frange(u.start, u.end, fps)}`).join(' · ')}</div>
          <textarea data-note rows="2" placeholder="${ta('Anything to change before saving? e.g. “sparks need bright heads”')}" style="margin-top:8px">${esc(pk.note || '')}</textarea></div></div>`;
      }).join('')}</div>`;
  }).join('<hr>') + '<div id="repbox" class="panel md" style="margin-top:18px" hidden></div>';
  $$('[data-job]', el).forEach(b => b.onclick = async () => {
    const pre = b.closest('.panel').querySelector('pre.log');
    const j = await startJob(b.dataset.job, {project: P.name}, false);
    if (!j) return;
    pre.hidden = false; pre.textContent = '';
    $$('[data-job]', el).forEach(x => { x.disabled = true; });
    followJob(j.id, pre, jj => {
      $$('[data-job]', el).forEach(x => { x.disabled = false; });
      toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
      if (b.dataset.job === 'resolve_diff') api('/api/project/' + encodeURIComponent(P.name)).then(NP => { Object.assign(P, NP); });
    });
  });
  $$('.fx', el).forEach(box => {
    const k = box.dataset.fx;
    $('[data-pick]', box).onchange = e => { (picks[k] = picks[k] || {}).pick = e.target.checked; box.classList.toggle('picked', e.target.checked); $('#psaved').textContent = t('saving…'); savePicks(); };
    $('[data-note]', box).oninput = e => { (picks[k] = picks[k] || {}).note = e.target.value; $('#psaved').textContent = t('saving…'); savePicks(); };
  });
  $$('.fx img', el).forEach(img => { img.onclick = () => { const lb = $('#lightbox'); $('img', lb).src = img.src; $('.lbcap', lb).textContent = img.title; lb.hidden = false; }; });
  $$('.showrep', el).forEach(a => a.onclick = async e => {
    e.preventDefault();
    const box = $('#repbox'); const rep = await api('/api/text?path=' + encodeURIComponent(a.dataset.rep));
    box.innerHTML = md(rep.text); box.hidden = false; box.scrollIntoView({behavior: 'smooth'});
  });
}
