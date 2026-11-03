/* MotionLab app - js/edit.js: the Editor's list (#/edit), Bulk, New edit (its steps).
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ projects
// one card per video (the user, 2026-10-15: "the blocks are so big and show random info - it should at least show a
// preview of some render; clips, footage, versions / renders / in Resolve are good but very unorganized"): the newest
// render's picture (it plays, muted, while the pointer is on it) with the date of that render, the name, its length;
// the clips (or Generate's icon: made from zero) and the user's rating - or "Not reviewed yet" when the newest render
// has no rating yet (the user, the same day: "remove 1 version 1 render; remind the person"); newest render first
const RATE = {good: ['ok', t('Good')], ok: ['amber', t('OK')], bad: ['bad', t('Bad')]};
// the months as the language shortens them: Oct · oct (a date = "12 Oct 2025" / "12 oct 2025")
const MONTHS = LANG === 'en' ? ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  : Array.from({length: 12}, (_, i) => new Intl.DateTimeFormat(LANG, {month: 'short'}).format(new Date(2026, i, 15)).replace(/\.$/, ''));
// a time (seconds since 1970) in words: today 01:37 / yesterday 18:20 / 3 days ago / 12 Oct (+ the year if not this one);
// day = a date without a time: today / yesterday
const whenWords = (ts, day = false) => {
  if (!ts) return '';
  const d = new Date(ts * 1000), now = new Date(), d0 = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const n = Math.round((d0(now) - d0(d)) / 864e5), hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return n <= 0 ? (day ? t('today') : t('today {hm}', {hm})) : n === 1 ? (day ? t('yesterday') : t('yesterday {hm}', {hm}))
    : n < 7 ? t('{n} days ago', {n})
    : `${d.getDate()} ${MONTHS[d.getMonth()]}${d.getFullYear() !== now.getFullYear() ? ' ' + d.getFullYear() : ''}`;
};
// the lab's own date strings ("2026-10-15", "2026-10-15 14:07", ISO): with a time = whenWords, a day only = without one
const strTime = s => { const m = /^(\d{4})-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d))?/.exec(String(s || ''));
  return m ? new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0)).getTime() / 1000 : 0; };
const whenStr = s => { const ts = strTime(s); return ts ? whenWords(ts, !/[ T]\d\d:\d\d/.test(s)) : ''; };
const pname = p => p.label || p.name;       // the name the app shows (Rename); the folder keeps its own
const genChip = () => `<span class="pgen" title="${ta('Made from zero (Generator) - no clips of your own')}"><svg class="i"><use href="#i-generate"/></svg>${t('Generated')}</span>`;
const reviewChip = (p, L) => !L ? '' : p.reviewed ? (rateChip(p.rating) || `<span class="prate ok" title="${ta('you rated its parts (How did it turn out?)')}">${t('Reviewed')}</span>`)
  : `<span class="prate todo" title="${p.rating ? ta('your rating ({rating}) was for an older render', {rating: RATE[p.rating] ? RATE[p.rating][1] : p.rating})
    : ta('How did it turn out? - rate it on its Review tab')}">${t('Not reviewed yet')}</span>`;
const picUrl = pc => !pc ? '' : pc.image ? fileUrl(pc.image) : `/api/thumb?video=${encodeURIComponent(pc.video)}&f=${pc.f}&fps=${pc.fps}`;
const lenWords = (frames, fps) => { if (!frames || !fps) return ''; const s = frames / fps;
  return s >= 60 ? `${Math.floor(s / 60)}:${pad(Math.round(s % 60))} min` : `${Math.round(s)} s`; };
const shapeWord = (w, h) => !w || !h ? '' : w > h * 1.1 ? t('horizontal') : h > w * 1.1 ? t('vertical') : t('square');
const rateChip = r => rvChip('result', r, t('your overall rating (How did it turn out?)'));     // the review's own chip (2026-10-18)
function projCard(p) {
  const L = p.latest, href = '#/project/' + encodeURIComponent(p.name), pc = p.picture;
  const now = L ? lenWords(L.frames, L.fps) || t('rendered') : p.plans.length ? `<span class="amber">${t('not rendered yet')}</span>` : `<span class="muted">${p.generated ? t('not made yet') : t('no edit yet')}</span>`;
  const fr = pc && pc.video ? `f${pc.f} (${tc(pc.f, pc.fps)})` : '';
  return `<div class="card pcard">${newTag(`p:${p.name}@${Math.round(p.done_t || 0)}`, p.done_t)}<a class="clink" href="${href}">
    <div class="ppic"${L ? ` data-v="${esc(L.rel)}" data-t="${pc && pc.video === L.rel ? (pc.f + 0.5) / pc.fps : 0}"` : ''}>${pc ? `<img src="${picUrl(pc)}" loading="lazy" alt=""
      ${pc.video ? `title="${L && pc.video === L.rel ? ta('{frame} of the newest render', {frame: fr}) : fr}"` : ''}>` : `<svg class="ic"><use href="#i-${p.generated ? 'generate' : 'edit'}"/></svg>`}
      <span class="pbadges">${p.title ? `<span class="pbadge" title="${ta('title, thumbnails and description are ready')}">${t('ready to post')}</span>` : ''}${p.resolve.length ? `<span class="pbadge r" title="${ta('also built as a DaVinci Resolve project')}">Resolve</span>` : ''}</span>
      <span class="pwhen" title="${L ? ta('the newest render: {date}', {date: L.modified}) : ta('made {when}', {when: whenWords(p.created)})}">${L ? esc(whenWords(L.mtime)) : t('made {when}', {when: esc(whenWords(p.created))})}</span>${L ? '<span class="pplay">▶</span>' : ''}</div>
    <div class="cb"><span class="ct">${esc(pname(p))}</span><div class="small">${now}</div></div></a>
    <div class="pfacts"><span>${p.clips ? `${tn(p.clips, '<b>{n}</b> clip', '<b>{n}</b> clips')} · ${bytes(p.footage_bytes)}` : p.generated ? genChip() : `<span class="muted">${t('no clips yet')}</span>`}</span>
      ${reviewChip(p, L)}</div>
    <span class="pdel"><button class="btn sm ghost icon" data-ren="${esc(p.name)}" title="${ta('Rename…')}"><svg class="i"><use href="#i-pen"/></svg></button>${delBtn('project', p.name)}</span></div>`;
}
// Rename (the user, 2026-10-15: "I can't rename my edits?"): the name the app shows - build\project.json "label";
// the folder keeps its name, so the clips, the edits and a Resolve project still find everything
function renameModal(p) {
  modal(`<h2>${t('Rename')}</h2><div class="small muted" style="margin-top:-4px">${t('The name MotionLab shows for this video. Its folder stays “{folder}”, so your clips, edits and Resolve still find everything.', {folder: esc(p.name)})}</div>
    <input type="text" id="rnname" value="${esc(pname(p))}" maxlength="80" style="width:100%;margin-top:14px">
    <div class="row" style="margin-top:14px"><button class="btn pri" id="rnok">${t('Save')}</button><button class="btn" id="rnno">${t('Cancel')}</button>
      ${p.label ? `<span class="grow"></span><a href="#" class="small" id="rnback">${t('Back to “{name}”', {name: esc(p.name)})}</a>` : ''}</div>`, el => {
    const inp = $('#rnname', el); inp.focus(); inp.select();
    const save = async label => {
      try { await api(`/api/project/${encodeURIComponent(p.name)}/rename`, {label}); closeModal(); toast(t('Renamed'), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
    $('#rnok', el).onclick = () => { const v = inp.value.trim(); if (!v) { inp.focus(); return; } save(v); };
    inp.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); $('#rnok', el).click(); } };
    $('#rnno', el).onclick = closeModal;
    const bk = $('#rnback', el); if (bk) bk.onclick = e => { e.preventDefault(); save(''); };
  });
}
// a video made from zero shows in the Generator only, until the user moves it to the Editor (0.4.3.5)
const inGenerator = p => !!p.generated && !p.in_editor;
async function pageProjects(main) {
  const [all, BAT] = await Promise.all([api('/api/projects'), api('/api/batches?kind=recreate').catch(() => [])]);
  const ps = all.filter(p => !inGenerator(p)).sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));
  const cv = big => `<button class="btn pri${big ? ' big' : ''}" id="cvnew"><svg class="i"><use href="#i-edit"/></svg>${t('New edit')}</button>`;
  const many = ps.filter(p => p.clips).length >= 2;
  main.innerHTML = `<div class="head"><div><h1>${t('Editor')}</h1><div class="sub">${t('Your clips, cut like videos you analysed, the way you say - or from a prompt.')}</div></div></div>
    ${ps.length ? `<div class="toprow">${cv(true)}${many ? `<button class="btn ghost big" id="bkedit" title="${ta('One style for several of your videos - quick drafts, or one Claude window for all of them')}"><svg class="i"><use href="#i-videos"/></svg>${t('Edit several videos')}</button>` : ''}<span class="grow"></span><button class="btn" data-open="projects" title="${ta('the folder with all your videos')}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>` : ''}
    ${batchRows(BAT)}
    ${ps.length ? `<div class="cards pcards">${ps.map(projCard).join('')}</div>`
      : emptyHero('edit', t('Make your first edit'), t('Your clips and a style - up to three videos you analysed, or your own words. A quick draft takes minutes; Claude makes it great.'), cv(true))}`;
  $('#cvnew', main).onclick = () => newEdit();
  const bk = $('#bkedit', main); if (bk) bk.onclick = () => bulkEditModal();
  wireBatchRows(main, () => pageProjects(main));
  wirePcards(main, ps);
}
// ---- Bulk (0.4.5, the user: "bulk analyze thumbnails, videos, and also bulk edit stuff or generate"): a batch that
// Claude has not finished (its window stopped - a limit, closed) waits here with *Continue the batch* (the skill skips
// what is done); ✕ forgets it (the videos stay as they are)
function batchRows(B) {
  return (B || []).map(b => {
    const v = {done: b.done.length, videos: plural(b.items.length, 'video'), when: esc(whenStr(b.created)), left: plural(b.left.length, 'video')};
    return `<div class="bkrow"><svg class="i"><use href="#i-claude"/></svg><span class="grow">${b.kind === 'review'
      ? t('<b>Claude checked {done} of {videos}</b> of the batch from {when} - {left} left', v)
      : t('<b>Claude edited {done} of {videos}</b> of the batch from {when} - {left} left', v)}</span>
    ${claudeBtn(b.prompt, t('Continue the batch'), b.task, `batch of ${b.left.length}`, 'sm pri')}<button class="btn sm ghost" data-bkforget="${esc(b.id)}" title="${ta('Forget this batch (the videos stay as they are)')}">✕</button></div>`;
  }).join('');
}
function wireBatchRows(main, redraw) {
  $$('[data-bkforget]', main).forEach(x => x.onclick = async () => {
    try { await api('/api/batches/forget', {id: x.dataset.bkforget}); redraw(); } catch (e) { toast(e.message, 'err'); }
  });
}
// Editor > Edit several videos (0.4.5): 2-10 of your videos, one style (up to 3 analysed videos, or presets + your
// words), optional length / format; then a quick draft each (queued jobs, no Claude) or ONE Claude window for all
// (/recreate-video batch <id>) - Claude's usual time per edit on this PC said first
async function bulkEditModal() {
  const [ps, S, OPT, EST] = await Promise.all([api('/api/projects'), loadStyles(), api('/api/edit/options'), api('/api/estimate').catch(() => ({}))]);
  const vids = ps.filter(p => !inGenerator(p) && p.clips).sort((a, b) => (b.sort_t || 0) - (a.sort_t || 0));
  const st = {how: 'style', like: [], presets: [], length: '', format: ''};
  modal(`<h2>${t('Edit several videos the same way')}</h2>
    <div class="avstep"><b>1</b><span>${t('Which videos?')}</span><span class="small muted">${t('2 to {max} - each keeps its own clips and the song in its folder', {max: AV_MAX})}</span></div>
    <div class="avfiles" id="bkv">${vids.map(p => `<label class="avfile"><input type="checkbox" value="${esc(p.name)}"><span class="grow">${esc(pname(p))}</span><span class="small dim">${plural(p.clips, 'clip')}${p.renders && p.renders.length ? ' · ' + t('edited before') : ''}</span></label>`).join('')}</div>
    <div class="avstep"><b>2</b><span>${t('In which style?')}</span></div>
    <div class="seg" id="bkhow"><button data-v="style">${t('Like videos you analysed')}</button><button data-v="words">${t('The way you say')}</button></div>
    <div id="bkstyle" style="margin-top:8px"></div>
    <div id="bkwords" hidden style="margin-top:8px"><div class="gpre">${OPT.presets.map(x => `<button class="fchip" data-p="${esc(x.id)}" title="${esc(t(x.help))}">${esc(t(x.label))}</button>`).join('')}</div>
      <textarea id="bkwant" rows="2" placeholder="${ta('…and / or in your words, e.g. fast cuts on the beat, captions word by word')}" style="margin-top:8px"></textarea></div>
    <div class="nestep opt" style="margin-top:12px"><b>3</b>${t('Length and format')} ${optTag()}</div>
    <div class="nedet"><label>${t('Length')}</label><div class="seg" id="bklen">${[['', t('Auto')], ['15', '15 s'], ['30', '30 s'], ['45', '45 s'], ['60', '1 min']].map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div>
      <label>${t('Format')}</label><div class="seg" id="bkfmt">${[['', t('Auto')], ['vertical', t('Vertical 9:16')], ['horizontal', t('Horizontal 16:9')], ['square', t('Square')]].map(([v, l]) => `<button data-v="${v}">${l}</button>`).join('')}</div></div>
    <div class="row" style="margin-top:16px"><button class="btn big" id="bkdraft" disabled>${t('Quick drafts now')}</button>
      <button class="btn pri big" id="bkclaude" disabled><svg class="i"><use href="#i-claude"/></svg>${t('Make them with Claude')}</button></div>
    <div class="small muted" id="bksum" style="margin-top:8px"></div>`, el => {
    const picked = () => $$('#bkv input:checked', el).map(x => x.value);
    const upd = () => {
      const n = picked().length, styled = st.how === 'style' ? st.like.length > 0 : st.presets.length > 0 || $('#bkwant', el).value.trim();
      const ok = n >= 2 && n <= AV_MAX && styled;
      $('#bkdraft', el).disabled = $('#bkclaude', el).disabled = !ok;
      $('#bkstyle', el).hidden = st.how !== 'style'; $('#bkwords', el).hidden = st.how !== 'words';
      $('#bksum', el).innerHTML = n < 2 ? t('Pick at least two videos.') : n > AV_MAX ? t('At most {n} at a time.', {n: AV_MAX}) : !styled ? t('Pick a style.')
        : t('<b>Quick drafts</b>: a first edit of each in minutes, made by rules - no Claude. <b>With Claude</b>: one window edits them one after another - {time}.', {time: estWords(EST.recreate, n, 'edit')});
    };
    spSeg(el, '#bkhow', st, 'how', upd); spSeg(el, '#bklen', st, 'length'); spSeg(el, '#bkfmt', st, 'format');
    stylePicker($('#bkstyle', el), st, {S, purpose: 'edit', max: OPT.max_refs, onChange: upd});
    $$('[data-p]', el).forEach(b => b.onclick = () => {
      const i = st.presets.indexOf(b.dataset.p);
      if (i >= 0) st.presets.splice(i, 1); else st.presets.push(b.dataset.p);
      b.classList.toggle('on', i < 0); upd();
    });
    $('#bkv', el).onchange = upd; $('#bkwant', el).oninput = upd;
    const go = async mode => {
      $('#bkdraft', el).disabled = $('#bkclaude', el).disabled = true;
      try {
        const r = await api('/api/edit/batch', {projects: picked(), mode, request: {how: st.how, like: st.how === 'style' ? st.like : [],
          presets: st.how === 'words' ? st.presets : [], want: st.how === 'words' ? $('#bkwant', el).value : '', length_s: st.length || null,
          format: st.format || null, sound: 'auto', resolve: false}});
        closeModal();
        if (mode === 'claude') openClaude(r.prompt, 'recreate', r.label);
        else { ping(); toast(t('{drafts} on the way - one after another', {drafts: plural(r.jobs.length, 'quick draft')}), 'ok'); }
        route();
      } catch (e) { toast(e.message, 'err'); upd(); }
    };
    $('#bkdraft', el).onclick = () => go('drafts');
    $('#bkclaude', el).onclick = () => go('claude');
    upd();
  }, 'wide');
}
// the video cards' Rename pencils + the render playing while the pointer is on its picture (Editor, Generator)
function wirePcards(main, ps) {
  $$('[data-ren]', main).forEach(b => b.onclick = e => { e.preventDefault(); renameModal(ps.find(x => x.name === b.dataset.ren)); });
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  $$('.ppic[data-v]', main).forEach(box => {          // the render plays while the pointer is on its picture
    box.onmouseenter = () => {
      if ($('video', box)) return;
      const v = document.createElement('video');
      Object.assign(v, {muted: true, loop: true, playsInline: true, preload: 'auto'});
      v.onloadedmetadata = () => { v.currentTime = +box.dataset.t || 0; v.play().catch(() => {}); };
      v.onplaying = () => box.classList.add('playing');
      v.src = fileUrl(box.dataset.v); box.appendChild(v);
    };
    box.onmouseleave = () => { const v = $('video', box); box.classList.remove('playing');
      if (v) { v.pause(); v.removeAttribute('src'); v.load(); v.remove(); } };
  });
}

// ---- Editor > New edit: a pop-up of steps (2026-10-22, the user: "the edit a video is our most powerful tool so we
// kinda need to expand to give Claude the most options and customability ... simplicity and clarity rather than having
// everything in a single section"; after a page that day: "still make it a pop up as before? and just show section per
// section, make the sidebar steps with numbers isntead of letters, and make a line go through them so the user know
// where to go", in the look of their mock-up new_edit_section.html; then: "a little preview when we have selected
// clips ... manage them? delete ... there is too much text and it clutters the vision of the user ... less text and
// more colors, icons and more distinct"). One step on screen at a time - 1 Clips (the clips as pictures), 2 Text (what
// it is about | the words on screen, a script or brief from Prepare), 3 References (picture cards), 4 Style, 5 Sound,
// 6 Final (length, format, the summary, Claude's time) - Back / Next in the footer; on the left the steps on a line:
// done = a tick and the short answer, the one on screen = Now, the line gold up to it (a click jumps there). Words
// only where a picture or an icon cannot say it; the rest in tooltips. Only the clips are needed: what is left on Auto
// is Claude's call. One function per step draws it, writes ne.st and may return a refresh (run on every change);
// neRows = what was picked, read by the steps and the summary. Saved as build\edit_request.json + build\edit_brief.md
// (POST /api/project/<p>/edit_request, motionlab\editreq.py): Claude (/recreate-video request <p>) and the quick draft
// read it. Was a four-step dialog (0.4 - 0.5.1, createVideoModal).
const NE_STEPS = [   // [id, the name on the left, the step's title, its icon + colour in the summary]
  ['clips', t('Clips'), t('Choose your clips'), 'i-videos', '--amber'],
  ['text', t('Text'), t('Give Claude context'), 'i-pen', '--cyan'],
  ['refs', t('References'), t('Add references'), 'i-refs', '--pink'],
  ['style', t('Style'), t('Pick the style'), 'i-palette', '--violet'],
  ['sound', t('Sound'), t('How does it sound?'), 'i-music', '--green'],
  ['final', t('Final'), t('Last details'), 'i-clock', '--amber'],
  ['segs', t('Segments'), t('Each part, your way'), 'i-film', '--cyan']];       // 0.6.1: Edit by segments (neSegs)
const neIcon = (id, colour = '') => `<svg class="i"${colour ? ` style="color:var(${colour})"` : ''}><use href="#${id}"/></svg>`;
const neTalk = id => /^(script|hook)-/.test(id || '');          // a talking script / hook: the user films it
async function newEdit(pre = {}) {    // pre = {project, from: 'reference' | 'prompt', pick}
  let S, PRM, ps, OPT;
  try { [S, PRM, ps, OPT] = await Promise.all([loadStyles(), api('/api/prompts'), api('/api/projects'), api('/api/edit/options')]); }
  catch (e) { toast(e.message, 'err'); return; }
  const pick = pre.from === 'prompt' ? pre.pick || '' : '';
  const st = {src: pre.project && ps.some(x => x.name === pre.project) ? 'old' : ps.length ? '' : 'new', project: pre.project || '', newp: '',
              about: '', onscreen: '', prompt: pick, like: pre.from === 'reference' && pre.pick ? [pre.pick] : [], exact: false,
              where: '', type: '', rhythm: '', moods: [], captions: '', presets: [], want: '', palette: [],
              sound: neTalk(pick) ? 'talk' : 'auto', ambience: '', sfx: '', kinds: [], sounds: [], snotes: '', length: '', format: '', resolve: false,
              photos: {}, products: [], framing: ''};
  const ne = {S, PRM, ps, OPT, st, cur: 0};
  ne.proj = () => st.src === 'old' ? st.project : st.src === 'new' ? st.newp : '';
  ne.P = () => ps.find(x => x.name === ne.proj());
  const N = NE_STEPS.length;
  modal(`<div class="nemw"><div class="nehd"><div class="nehdt"><h2>${t('New edit')}</h2><p>${t('Your clips, edited the way you want. They are only read, never changed.')}</p></div>
      <div class="brandrow nebrandtop" id="nebrand"></div></div>
    <nav class="nenav">${NE_STEPS.map(([id, name], i) => `<button data-go="${id}"${id === 'clips' ? '' : ' class="opt"'}><b>${i + 1}</b><span>${name}<small></small></span></button>`).join('')}</nav>
    <div class="nepanes">${NE_STEPS.map(([id, , title]) => `<section class="nesec" id="ne-${id}" hidden><h2 class="nest">${title}${id === 'clips' ? '' : optTag()}<span class="nestx"></span></h2><div class="nesecb"></div></section>`).join('')}</div>
    <div class="nefoot"><span class="small muted" id="nepos"></span>
      <button class="btn" id="neback">${t('← Back')}</button><button class="btn pri" id="nenext"></button>
      <button class="btn" id="cvdraft" disabled><svg class="i"><use href="#i-generate"/></svg>${t('Quick draft now')}</button>
      <button class="btn pri" id="cvgo" disabled><svg class="i"><use href="#i-claude"/></svg>${t('Make it with Claude')}</button>
      <button class="btn pri" id="cvbuild" hidden disabled title="${ta('Every part with its edit, on your cuts - then the video is rendered')}"><svg class="i"><use href="#i-film"/></svg>${t('Build the edit')}</button></div></div>`, el => {
    ne.el = el;
    const draw = {clips: neClips, text: neText, refs: neRefs, style: neStyle, sound: neSound, final: neFinal, segs: neSegs};
    const refresh = [];
    ne.changed = () => refresh.forEach(f => f());
    NE_STEPS.forEach(([id]) => { const f = draw[id]($(`#ne-${id} .nesecb`, el), ne); if (f) refresh.push(f); });
    refresh.push(() => neNav(el, ne));
    el.addEventListener('change', e => { if (e.target.closest('#nebrand')) ne.changed(); });    // For my brand: the look counts
    const go = id => {
      const i = NE_STEPS.findIndex(s => s[0] === id); if (i < 0) return;
      const last = i === N - 1, fin = id === 'final';        // (Final: the quick draft, Claude, or on to Segments)
      ne.cur = i;
      NE_STEPS.forEach(([sid], j) => { $(`#ne-${sid}`, el).hidden = j !== i; });
      $('.nepanes', el).scrollTop = 0;
      $('#nepos', el).textContent = t('Step {n} of {total}', {n: i + 1, total: N});
      $('#nepos', el).hidden = last || fin;
      $('#neback', el).hidden = !i;
      $('#nenext', el).hidden = last; if (!last) $('#nenext', el).textContent = `${t('Next: {step}', {step: NE_STEPS[i + 1][1]})} →`;
      $('#nenext', el).classList.toggle('pri', !fin);
      $('#cvdraft', el).hidden = !fin;
      $('#cvgo', el).hidden = !fin && !last;                 // (Segments too, step 7: Claude picks the parts you left)
      $('#cvgo', el).classList.toggle('pri', !last);
      $('.nefoot', el).classList.toggle('last', last);
      $('#cvbuild', el).hidden = !last;
      if (id === 'segs' && ne.segEnter) ne.segEnter();
      ne.changed();                                          // (its buttons' tooltips follow the step)
    };
    $$('.nenav button', el).forEach(b => b.onclick = () => go(b.dataset.go));
    $('#neback', el).onclick = () => go(NE_STEPS[ne.cur - 1][0]);
    $('#nenext', el).onclick = () => go(NE_STEPS[ne.cur + 1][0]);
    const save = () => api(`/api/project/${encodeURIComponent(ne.proj())}/edit_request`, {...neBody(st), brand: brandOn(el, '#nebrand')});
    $('#cvgo', el).onclick = async () => {
      try { const pj = ne.proj(), r = await save();
        openClaude(r.command, 'recreate', `${r.request.how} → ${pj}`); closeModal(); location.hash = '#/project/' + encodeURIComponent(pj); }
      catch (e) { toast(e.message, 'err'); }
    };
    $('#cvdraft', el).onclick = async () => {
      try { const pj = ne.proj(); await save();
        await api('/api/jobs', {kind: 'draft', args: {project: pj}, queue: true});
        toast(t('The quick draft is on its way - it shows up here when it is ready'), 'ok'); closeModal(); location.hash = '#/project/' + encodeURIComponent(pj); }
      catch (e) { toast(e.message, 'err'); }
    };
    $('#cvbuild', el).onclick = async () => {                 // 7: every part as picked, on the cuts, then rendered
      const S = ne.segs && ne.segs();
      if (!S || !S.plan) return;
      try { const pj = ne.proj();
        await api('/api/jobs', {kind: 'segments_build', args: {project: pj, plan: S.plan}, queue: true});
        toast(t('Your edit is being built - it shows up here when it is ready'), 'ok'); closeModal(); location.hash = '#/project/' + encodeURIComponent(pj); }
      catch (e) { toast(e.message, 'err'); }
    };
    ne.save = save;
    ne.go = go;
    ne.changed(); go('clips');
  }, 'wide nemodal');
}

// 1. Clips: the clips of a video they already have ("old") or new clips copied into a new video ("new", st.newp once
// made) - the two wide cards of 2026-10-16 (the user: "choose between an old video clip or new clips, intuitive and
// distinct") - then the video's clips as pictures (GET /api/project/<p>'s sources, a frame each by /api/thumb): a click
// plays one in the PC's player, the bin moves one to the Recycle Bin after a yes here (the app's delete route, a file
// in the video's folder: trash.plan_file - the user's click, never Claude's), the + tile (or a drop) copies more in;
// the folder's songs as chips under them. ne.addFiles = the copy, also used by 5's *Add a song…*.
// 2026-10-24 (a friend's asks): *Add a folder…* (or a folder dropped - sub-folders too, clipsFromDrop / clipNames),
// never a Mac's / iPhone's ._ files (isJunk), photos as photos (a PHOTO badge, its own picture, how long it shows -
// st.photos -> edit_request "photos"), and the new video's name stays editable (POST .../rename = its label).
function neClips(box, ne) {
  const {st, ps} = ne;
  ne.clips = {};                     // per video: its clips as the server lists them (loaded once, again after a change)
  box.innerHTML = `<div class="cvchoice nesrc">
      <button class="cvopt" data-src="old" ${ps.length ? '' : 'disabled'}><svg class="ic"><use href="#i-videos"/></svg><b>${t('Clips you already have')}</b>
        <span>${ps.length ? plural(ps.length, 'video') : t('No video yet - start with new clips')}</span></button>
      <button class="cvopt" data-src="new"><svg class="ic"><use href="#i-upload"/></svg><b>${t('New clips')}</b><span>${t('From your PC - copied in')}</span></button></div>
    <div class="nesrcrow" id="nesrc-old" hidden>${neIcon('i-videos', '--amber')}<select id="cvp">${ps.map(x => `<option value="${esc(x.name)}">${esc(pname(x))} (${plural(x.clips, 'clip')})</option>`).join('')}</select>
      <span class="small muted" id="necount"></span><button class="btn sm ghost" id="nefold" title="${ta("the video's folder: your clips and everything made from them")}"><svg class="i"><use href="#i-folder"/></svg>${t('Folder')}</button></div>
    <div class="nesrcrow" id="nesrc-new" hidden>${neIcon('i-pen', '--amber')}<input type="text" id="cvname" placeholder="${ta('Name the video, e.g. cooking vlog 1')}" title="${ta('Leave it empty to name it after the first clip.')}"></div>
    <div id="neclips"></div><div id="nerm"></div><div id="cvfiles"></div>`;
  const sel = $('#cvp', box), name = $('#cvname', box), rel = (pj, f) => `projects/${pj}/${f}`;
  if (st.src === 'old') sel.value = st.project; else st.project = sel.value;
  const load = async pj => {
    ne.clips[pj] = 'loading';
    let list = [];
    try { list = (await api('/api/project/' + encodeURIComponent(pj))).sources.filter(s => s.exists !== false); } catch (e) { toast(e.message, 'err'); }
    ne.clips[pj] = list;
    const P = ps.find(x => x.name === pj), o = [...sel.options].find(x => x.value === pj);
    if (P) { P.clips = list.length; if (o) o.textContent = `${pname(P)} (${plural(P.clips, 'clip')})`; }   // the count the list shows, kept true
    ne.changed();
  };
  const PH_S = [3, 5, 8];                             // a photo's length in the edit: a click on its pill goes round these
  const phS = n => (st.photos[n] || {}).seconds || 5;
  const tile = (pj, c) => { const ph = c.photo || PHOTO_EXT.test(c.name);
    return `<div class="neclip${ph ? ' photo' : ''}" title="${esc(c.name)}">
      <button class="neclipv" data-play="${esc(c.name)}" title="${ph ? ta('Open the photo') : ta('Play it')}"><img src="/api/thumb?video=${encodeURIComponent(rel(pj, c.name))}&f=${ph ? 0 : 12}&fps=25" loading="lazy" alt="" onerror="this.remove()">
        <svg class="i"><use href="#${ph ? 'i-thumb' : 'i-play'}"/></svg>${ph ? `<b class="nephoto">${t('PHOTO')}</b>` : c.duration_s ? `<i>${ytOf(c.duration_s, 1)}</i>` : ''}</button>
      <span class="neclipn">${esc(c.name)}</span>
      ${ph ? `<button class="nephs" data-phs="${esc(c.name)}" title="${ta('The longest the photo shows in the edit - click to change')}">${t('{n} s', {n: phS(c.name)})}</button>` : ''}
      <button class="neclipx" data-rm="${esc(c.name)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg></button></div>`; };
  let drawn = '';
  const paint = () => {
    const pj = ne.proj(), P = ne.P(), songs = (P || {}).songs || [];
    $$('.nesrc .cvopt', box).forEach(b => b.classList.toggle('on', b.dataset.src === st.src));
    $('#nesrc-old', box).hidden = st.src !== 'old'; $('#nesrc-new', box).hidden = st.src !== 'new';
    name.title = st.newp ? t('The name MotionLab shows for this video - change it whenever you like') : t('Leave it empty to name it after the first clip.');
    let C = pj ? ne.clips[pj] : [];
    if (pj && C === undefined) { load(pj); C = ne.clips[pj]; }
    const key = JSON.stringify([st.src, pj, C, songs, st.photos]);
    if (key === drawn) return;                         // the grid only when its clips change (not on every key typed)
    drawn = key;
    const el = $('#neclips', box), clips = Array.isArray(C) ? C : [];
    $('#necount', box).textContent = P ? [plural(clips.length, 'clip'), songs.length ? plural(songs.length, 'song') : ''].filter(Boolean).join(' · ') : '';
    $('#nefold', box).dataset.open = 'projects/' + pj;
    if (!st.src) { el.innerHTML = ''; return; }
    const big = !clips.length;
    el.innerHTML = C === 'loading' ? `<div class="small muted">${t('Loading…')}</div>` : `<div class="neclips${big ? ' empty' : ''}">${clips.map(c => tile(pj, c)).join('')}
        <label class="neadd${big ? ' big' : ''}" data-add="files"><input type="file" multiple hidden accept="${CLIP_ACCEPT}">${neIcon('i-plus')}
          <b>${big ? t('Drop your clips here') : t('Add clips…')}</b>${big ? `<span>${t('videos, photos or a whole folder - or click to choose them')}</span>` : ''}</label>
        <label class="neadd neaddf${big ? ' big' : ''}" data-add="folder" title="${ta('Every video, photo and song in a folder, its sub-folders too')}"><input type="file" hidden webkitdirectory multiple>${neIcon('i-folder')}
          <b>${t('Add a folder…')}</b>${big ? `<span>${t('sub-folders too')}</span>` : ''}</label></div>
      ${songs.length ? `<div class="nesongs">${songs.map(s => `<span class="nesong">${neIcon('i-music')}${esc(s)}<button class="neclipx" data-rm="${esc(s)}" title="${ta('Delete… (to the Recycle Bin)')}"><svg class="i"><use href="#i-trash"/></svg></button></span>`).join('')}</div>` : ''}`;
    const inp = $('[data-add=files] input', el), dir = $('[data-add=folder] input', el);
    if (inp) inp.onchange = () => { ne.addFiles([...inp.files]); inp.value = ''; };
    if (dir) dir.onchange = () => { ne.addFiles([...dir.files].map(f => ({file: f, path: f.webkitRelativePath || f.name})), undefined, true); dir.value = ''; };
    const grid = $('.neclips', el);
    if (grid) {
      grid.ondragover = e => { e.preventDefault(); grid.classList.add('on'); };
      grid.ondragleave = () => grid.classList.remove('on');
      grid.ondrop = async e => { e.preventDefault(); grid.classList.remove('on');
        try { const r = await clipsFromDrop(e.dataTransfer); ne.addFiles(r.files, undefined, r.folders); }
        catch (err) { toast(err.message, 'err'); } };
    }
    $$('[data-play]', el).forEach(b => b.onclick = () => api('/api/open', {path: rel(pj, b.dataset.play)}).catch(e => toast(e.message, 'err')));
    $$('[data-rm]', el).forEach(b => b.onclick = () => remove(b.dataset.rm));
    $$('[data-phs]', el).forEach(b => b.onclick = () => { const n = b.dataset.phs, s = PH_S[(PH_S.indexOf(phS(n)) + 1) % PH_S.length];
      st.photos[n] = {...(st.photos[n] || {}), seconds: s}; ne.changed(); });
  };
  // the bin: what the Delete dialog would say (GET /api/delete), here in the step - a pop-up over this one would lose it
  const remove = async file => {
    const pj = ne.proj(), r = rel(pj, file), host = $('#nerm', box);
    let pl;
    try { pl = await api(`/api/delete?kind=file&name=${encodeURIComponent(r)}`); } catch (e) { toast(e.message, 'err'); return; }
    const it = pl.items[0];
    host.innerHTML = `<div class="nerm"><svg class="i"><use href="#i-trash"/></svg><div class="grow"><b>${t('Remove {name}?', {name: esc(file)})}</b>
        <div class="small muted">${t('It goes to the Windows Recycle Bin - you can restore it from there.')} · ${bytes(it.bytes)}</div>
        ${it.warn.map(w => `<div class="small warnline">⚠ ${esc(t(w))}</div>`).join('')}</div>
      <button class="btn del" id="nermgo">${t('Move to the Recycle Bin')}</button><button class="btn" id="nermno">${t('Cancel')}</button></div>`;
    $('#nermno', host).onclick = () => { host.innerHTML = ''; };
    $('#nermgo', host).onclick = async () => {
      $('#nermgo', host).disabled = true;
      try {
        const res = await api('/api/delete', {kind: 'file', name: r, keys: pl.items.filter(x => x.default).map(x => x.key)});   // + a photo's old still-video copy
        if (res.failed.length) { host.innerHTML = `<div class="nerm"><span class="bad">${esc(t(res.failed[0].why))}</span></div>`; return; }
        host.innerHTML = ''; delete st.photos[file];
        toast(t('Moved to the Recycle Bin ({size}): {list}', {size: bytes(res.bytes), list: res.moved.join(', ')}), 'ok');
        const P = ne.P();
        if (P && (P.songs || []).includes(file)) { P.songs = P.songs.filter(s => s !== file); if (st.sound === 'music:' + file) st.sound = 'auto'; }
        delete ne.clips[pj];
        ne.changed();
      } catch (e) { toast(e.message, 'err'); $('#nermgo', host).disabled = false; }
    };
  };
  sel.onchange = () => { st.project = sel.value; $('#cvfiles', box).innerHTML = $('#nerm', box).innerHTML = ''; ne.changed(); };
  // the new video's name: before its folder exists it names the folder; after, it is the name MotionLab shows (the
  // folder keeps its own - the clips stay where they are), saved on Enter or when the field is left
  const rename = async () => {
    const v = name.value.trim(), P = ne.P();
    if (!st.newp || !P || !v || v === pname(P)) return;
    try { const r = await api(`/api/project/${encodeURIComponent(st.newp)}/rename`, {label: v});
      P.label = r.label || null; name.value = pname(P);
      const o = [...sel.options].find(x => x.value === st.newp); if (o) o.textContent = t('{name} (new)', {name: pname(P)});
      toast(t('Name saved: {name}', {name: pname(P)}), 'ok'); }
    catch (e) { toast(e.message, 'err'); }
  };
  name.onchange = rename;
  name.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); rename(); } };
  $$('.nesrc .cvopt', box).forEach(b => b.onclick = () => { if (st.busy || st.src === b.dataset.src) return;
    st.src = b.dataset.src; $('#cvfiles', box).innerHTML = $('#nerm', box).innerHTML = ''; ne.changed(); });
  // picked or dropped files -> the video's folder (a new video is made first, named by the user or after the first clip)
  // list = Files, or {file, path} from a folder (folder = true: the toast says what it found)
  ne.addFiles = async (list, rows = $('#cvfiles', box), folder = false) => {
    const all = [...list].map(x => x instanceof File ? {file: x, path: x.name} : x);
    const {clips: files, skipped} = clipNames(all);
    const odd = all.filter(x => !isJunk(x.file.name, x.path) && !CLIP_EXT.test(x.file.name));
    if (folder) toast(files.length ? tn(files.length, '{n} clip found in the folder', '{n} clips found in the folder')
      : t('No video, photo or sound files in that folder'), files.length ? 'ok' : 'err');
    else if (odd.length) toast(t('{files}: not a video, a photo or a sound file', {files: odd.map(x => x.file.name).join(', ')}), 'err');
    if (skipped && !folder && !odd.length) toast(t('Hidden files a Mac or an iPhone leaves next to clips were left out'));
    if (!files.length || st.busy) return;
    if (!st.src) { toast(t('First pick where your clips come from (1. Clips)'), 'err'); ne.go('clips'); return; }
    st.busy = true;
    try {
      if (st.src === 'new' && !st.newp) {
        let nm = name.value.trim();
        const top = folder && (all.find(x => x.path.includes('/')) || {}).path;           // a folder: named after it
        if (!nm) { const base = folderName(top ? top.split('/')[0] : files[0].name.replace(/\.[^.]+$/, '')); nm = base;
          for (let i = 2; ps.some(x => x.name.toLowerCase() === nm.toLowerCase()); i++) nm = `${base} ${i}`; }
        const r = await api('/api/projects/new', {name: nm});
        ps.unshift({name: r.name, label: null, clips: 0, songs: []}); st.newp = name.value = r.name;
        sel.insertAdjacentHTML('afterbegin', `<option value="${esc(r.name)}">${t('{name} (new)', {name: esc(r.name)})}</option>`);
      }
      const pj = ne.proj(), P = ne.P();
      for (const {file: f, name: nm} of files) {
        const row = document.createElement('div'); row.className = 'fifile';
        row.innerHTML = `<span class="grow">${esc(nm)} <span class="small muted">${bytes(f.size)}</span></span><span class="fibar"><i></i></span><span class="small" data-s>${t('copying…')}</span>`;
        rows.append(row);
        try {
          const r = await uploadClip(pj, f, neTalk(st.prompt) ? st.prompt : '', v => { $('.fibar i', row).style.width = `${Math.round(v * 100)}%`; }, nm);
          $('.fibar i', row).style.width = '100%'; row.classList.add('ok');
          $('[data-s]', row).textContent = r.kept ? t('already there') : r.file !== nm ? t('copied as {name} ✓', {name: r.file}) : t('copied ✓');
          if (!r.kept) { if (/\.(mp3|m4a|wav|aac|flac|ogg)$/i.test(nm)) (P.songs = P.songs || []).push(r.file); else P.clips++; }
        } catch (e) { row.classList.add('err'); $('[data-s]', row).textContent = e.message; }
      }
      delete ne.clips[pj];                             // listed again: the new clips show as pictures
      setTimeout(() => $$('.fifile.ok', rows).forEach(x => x.remove()), 2500);
    } catch (e) { toast(e.message, 'err'); }
    st.busy = false; ne.changed();
  };
  return paint;
}

// 2. Text: what Claude follows - what it is about | the words on screen as written (side by side), a script or brief
// from Prepare / the prompt library (the list, the picked one read beside it)
function neText(box, ne) {
  const {st, PRM} = ne, KL = Object.fromEntries(PRM.kinds.map(k => [k.id, k.label]));
  const items = PRM.items.filter(x => ['brief', 'script', 'hook'].includes(x.kind));
  const badge = x => `<span class="kbadge k-${esc(x.kind)}">${esc(t(KL[x.kind] || x.kind))}</span>`;
  box.innerHTML = `<div class="netwo"><div class="nef"><label for="neabout">${neIcon('i-pen', '--cyan')}${t('What is the video about?')}</label>
        <textarea id="neabout" rows="4" placeholder="${ta('e.g. a day at the climbing gym with my friends - funny, it ends with me finally reaching the top')}">${esc(st.about)}</textarea></div>
      <div class="nef"><label for="neons">${neIcon('i-type', '--pink')}${t('Text on screen')}</label>
        <textarea id="neons" rows="4" placeholder="${ta('One per line - e.g. DAY 1 OF 30')}">${esc(st.onscreen)}</textarea></div></div>
    <div class="nef"><label>${neIcon('i-scriptok', '--green')}${t('A script or brief from Prepare')}</label>
      <div class="nepick"><div class="nelist"><div class="nelq"><input type="search" id="cvq" placeholder="${ta('Search your scripts and briefs…')}"></div><div class="cvlist" id="cvpl"></div></div>
        <div class="neprev" id="neprev"></div></div></div>
    <div class="nef" id="neprod" hidden><label>${neIcon('i-bag', '--amber')}${t('Show a product')}
      <span title="${ta('From My Brand\'s catalogue - Claude puts it in a product card with its picture, price and your website')}">${t('up to {n}', {n: 2})}</span></label>
      <div class="neprods" id="neprods"></div></div>`;
  // product motion (0.6.0, My Brand step 5): My Brand's products for videos as picture cards; a picked one = when it
  // shows (in passing / at the end / both); Claude builds it from the template product-card
  brandData().then(b => {
    const cat = ((b || {}).catalogue || []).filter(p => p.use !== false && (p.name || '').trim()), hold = $('#neprods', box);
    if (!cat.length || !hold) return;
    $('#neprod', box).hidden = false;
    const HOW = [['passing', t('In passing')], ['end', t('At the end')], ['both', t('Both')]];
    const draw = () => {
      hold.innerHTML = cat.map(p => { const on = st.products.find(x => x.id === p.id), full = !on && st.products.length >= 2;
        return `<div class="neprod${on ? ' on' : ''}"><button class="neprb" data-p="${esc(p.id)}" ${full ? 'disabled' : ''}>
          <span class="neprp">${p.image ? `<img src="${fileUrl(p.image)}" alt="">` : neIcon('i-box', '--green')}</span>
          <span class="neprt"><b>${esc(p.name)}</b>${p.price ? `<span>${esc(p.price)}</span>` : ''}</span></button>
          ${on ? `<span class="neprh">${HOW.map(([h, l]) => `<button class="nech${on.how === h ? ' on' : ''}" data-h="${h}" data-p="${esc(p.id)}">${l}</button>`).join('')}</span>` : ''}</div>`; }).join('');
      $$('.neprb', hold).forEach(b2 => b2.onclick = () => { const id = b2.dataset.p;
        st.products = st.products.some(x => x.id === id) ? st.products.filter(x => x.id !== id) : [...st.products, {id, how: 'end'}].slice(0, 2);
        draw(); ne.changed(); });
      $$('.neprh .nech', hold).forEach(b2 => b2.onclick = () => { const x = st.products.find(y => y.id === b2.dataset.p); if (x) x.how = b2.dataset.h; draw(); ne.changed(); });
    };
    draw();
  });
  $('#neabout', box).oninput = e => { st.about = e.target.value; ne.changed(); };
  $('#neons', box).oninput = e => { st.onscreen = e.target.value; ne.changed(); };
  const prev = () => { const x = items.find(i => i.id === st.prompt);
    $('#neprev', box).innerHTML = x ? `<div class="row sp"><b>${esc(x.title || x.title_auto || x.id)}</b>${badge(x)}</div>
      <p class="neptext">${esc(x.text.slice(0, 480))}${x.text.length > 480 ? '…' : ''}</p>` : `<div class="neprev0">${neIcon('i-sparkle', '--amber')}<span>${t('Nothing picked - Claude works from your notes and your clips.')}</span></div>`; };
  const drawPrompts = q => {
    const row = x => `<label class="cvitem${x.id === st.prompt ? ' on' : ''}"><input type="radio" name="cvr" value="${esc(x.id)}" ${x.id === st.prompt ? 'checked' : ''}>
      <b class="grow">${esc(x.title || x.title_auto || x.id)}</b>${badge(x)}</label>`;
    const hits = items.filter(x => !q || [x.id, x.title, x.text, ...(x.tags || [])].join(' ').toLowerCase().includes(q)).slice(0, 60);
    $('#cvpl', box).innerHTML = items.length ? `<label class="cvitem${st.prompt ? '' : ' on'}"><input type="radio" name="cvr" value="" ${st.prompt ? '' : 'checked'}><b class="grow">${t('None')}</b></label>`
        + (hits.map(row).join('') || `<div class="empty">${t('No prompt matches.')}</div>`)
      : `<div class="empty">${t('No brief, script or hook yet - <a href="#/prompts" onclick="closeModal()">Prompts</a>.')}</div>`;
    $$('input[name=cvr]', box).forEach(r => r.onchange = () => {
      st.prompt = r.value; $$('#cvpl .cvitem', box).forEach(x => x.classList.toggle('on', $('input', x).checked));
      if (neTalk(st.prompt) && st.sound === 'auto') st.sound = 'talk';
      prev(); ne.changed(); });
  };
  $('#cvq', box).oninput = debounce(e => drawPrompts(e.target.value.trim().toLowerCase()), 150);
  drawPrompts(''); prev();
}

// 3. References: this PC's analysed videos as picture cards (up to OPT.max_refs, the count by the title) - their style,
// or an exact copy of one (two cards under them)
function neRefs(box, ne) {
  const {st, OPT} = ne, max = OPT.max_refs, vids = ownVideos(ne.S);
  let q = '', paintLook = () => {};
  box.innerHTML = `<div id="nebl"></div>${vids.length > 8 ? `<input type="search" class="nerq" placeholder="${ta('Search…')}">` : ''}<div class="nerefs"></div><div id="neexact"></div>`;
  const count = $('.nestx', box.closest('.nesec'));
  // My Brand's editing look (0.6.0, 2026-10-25): one card that picks the brand's videos at once
  brandData().then(b => {
    const look = (((b || {}).look || {}).like || []).filter(k => vids.some(v => v.key === k)), hold = $('#nebl', box);
    if (!look.length || !hold) return;
    const same = () => look.length === st.like.length && look.every(k => st.like.includes(k)), lg = ((b.identity || {}).logo);
    paintLook = () => {
      hold.innerHTML = `<button class="necard nebl${same() ? ' on' : ''}">${lg ? `<img src="${brandLogoSrc(lg, b.updated)}" alt="">` : neIcon('i-brand', '--pink')}
        <span><b>${t("My brand's look")}</b><span>${esc(look.map(k => (vids.find(v => v.key === k) || {}).label || k).join(' · '))}</span></span></button>`;
      $('button', hold).onclick = () => { st.like = same() ? [] : look.slice(0, max); st.exact = false; draw(); exact(); ne.changed(); };
    };
    paintLook();
  });
  const exact = () => {               // an exact copy needs one video analysed on this PC (every picked one is)
    const one = st.like.length === 1 && vids.some(v => v.key === st.like[0]);
    if (!one) st.exact = false;
    $('#neexact', box).innerHTML = st.like.length ? `<div class="neexact">
      <button class="necard nexo${st.exact ? '' : ' on'}" data-x="0"><svg class="ic"><use href="#i-palette"/></svg><span><b>${st.like.length > 1 ? t('In their style') : t('In its style')}</b><span>${t('your music, your length')}</span></span></button>
      <button class="necard nexo${st.exact ? ' on' : ''}" data-x="1" ${one ? '' : `disabled title="${ta('(one video analysed on this PC)')}"`}><svg class="ic"><use href="#i-copy"/></svg><span><b>${t('An exact copy')}</b><span>${t('the same song and cuts, with your clips')}</span></span></button></div>` : '';
    $$('.nexo', box).forEach(b => b.onclick = () => { st.exact = b.dataset.x === '1'; exact(); ne.changed(); });
  };
  const draw = () => {
    const keys = new Set(vids.map(v => v.key));
    const list = [...st.like.filter(k => !keys.has(k)).map(k => ({key: k, label: k})), ...vids]       // picked elsewhere (a test video)
      .filter(v => !q || [v.label, v.title, v.key, v.by, v.platform, v.category_label].join(' ').toLowerCase().includes(q));
    // a card = its picture, its length and its name (2026-10-22: "i dont care about the cuts per min stuff, maybe just
    // show duration and thats it"); the length = the end of its format label ("Horizontal · 2:35")
    $('.nerefs', box).innerHTML = vids.length ? list.map(v => { const on = st.like.includes(v.key), full = !on && st.like.length >= max,
      dur = (String(v.format || '').split(' · ')[1] || '').trim();
      return `<button class="necard neref${on ? ' on' : ''}" data-k="${esc(v.key)}" ${full ? 'disabled' : ''} title="${esc(v.line || v.summary || v.label || v.key)}">
        <span class="nerefp">${v.picture ? `<img src="${fileUrl(v.picture)}" loading="lazy" alt="">` : ''}${dur ? `<i>${esc(dur)}</i>` : ''}</span>
        <b>${esc(v.label || v.title || v.key)}</b></button>`; }).join('')
        || `<div class="small muted">${t('No video matches.')}</div>`
      : `<div class="empty">${t('No video analysed on this PC yet - add one in the <a href="#/analyze" onclick="closeModal()">Analyser</a>.')}</div>`;
    count.innerHTML = `<b>${st.like.length}</b> / ${max}`;
    paintLook();
    $$('.neref', box).forEach(b => b.onclick = () => { const k = b.dataset.k;
      st.like = st.like.includes(k) ? st.like.filter(x => x !== k) : [...st.like, k].slice(0, max); draw(); exact(); ne.changed(); });
  };
  const qi = $('.nerq', box);
  if (qi) qi.oninput = debounce(() => { q = qi.value.trim().toLowerCase(); draw(); }, 150);
  draw(); exact();
}

// one question's answers as pills: one answer (an Auto pill first; a second click clears) or several (st[key] a list,
// o.max; o.auto false = no Auto pill, nothing picked is Auto); o.help = where the picked answers' help goes (also each
// pill's tooltip); o.top = only that many answers (o.first
// first, then the table's order; a picked one always shows) and a "+N" pill for the rest (2026-10-22: "reduce the
// questions A LOT, to 4-5 options if possible and a '+' sign if u want to answer more")
function neChips(box, items, st, key, o = {}) {
  const many = Array.isArray(st[key]);
  const first = o.first || [], order = [...first.map(id => items.find(x => x.id === id)).filter(Boolean), ...items.filter(x => !first.includes(x.id))];
  let open = !o.top;
  const draw = () => {
    const picked = x => many ? st[key].includes(x.id) : st[key] === x.id;
    const shown = open ? order : order.filter((x, i) => i < o.top || picked(x)), more = order.length - shown.length;
    box.innerHTML = (many || o.auto === false ? '' : `<button class="nech${st[key] ? '' : ' on'}" data-v="">${t('Auto')}</button>`) + shown.map(x => {
      const on = picked(x), full = many && !on && o.max && st[key].length >= o.max;
      return `<button class="nech${on ? ' on' : ''}" data-v="${esc(x.id)}" ${full ? 'disabled' : ''} ${x.help ? `title="${esc(t(x.help))}"` : ''}>${esc(t(x.label))}</button>`; }).join('')
      + (more ? `<button class="nech nemore" title="${ta('Show all')}">+${more}</button>` : '');
    if (o.help) o.help.textContent = items.filter(x => x.help && picked(x)).map(x => many ? `${t(x.label)}: ${t(x.help)}` : t(x.help)).join(' · ');
    const m = $('.nemore', box); if (m) m.onclick = () => { open = true; draw(); };
    $$('button[data-v]', box).forEach(b => b.onclick = () => { const v = b.dataset.v;
      if (many) st[key] = st[key].includes(v) ? st[key].filter(x => x !== v) : [...st[key], v];
      else st[key] = st[key] === v ? '' : v;
      draw(); if (o.onChange) o.onChange(); });
  };
  draw();
}

// 4. Style (2026-10-22: "first make a row for the A ready-made style, then show the questions ... reduce ... to 4-5
// options ... and a '+' ... show the color palette without having to scroll down ... make it more big"): the ready-made
// styles in one row (their rhythm as bars: a shot each, the wider the longer; what each is = its tooltip), the
// questions as one compact card (the question on the left, at most 4 answers + "+N" on the right; where, the type, the
// rhythm, the mood, captions, the feel in their words), then the colour palette for titles, captions and graphics as
// big cards
const NE_Q = {where: ['i-pin', '--cyan'], type: ['i-film', '--violet'], rhythm: ['i-zap', '--amber'], moods: ['i-smile', '--pink'], captions: ['i-cc', '--green']};
const NE_FIRST = {type: ['vlog', 'ad', 'music_video', 'tutorial']};     // the kinds of video the user makes most, first
// the bars stay grey (2026-10-22: "dont put colors in ready-made style cuz that is for general feel of video" - colour
// is the palette's job, below)
const neBars = (r, hue = '#9a9aa6') => {
  const m = (r || {}).median_shot_s; if (!m) return '';
  const lo = r.p10_shot_s || m * 0.7, hi = r.p90_shot_s || m * 1.4, seq = [m, hi, lo, m, lo, hi, m, lo, hi, m, lo, m];
  const out = []; let sum = 0;
  for (let i = 0; sum < 9 && i < 40; i++) { const s = seq[i % seq.length]; sum += s;
    out.push(`<i style="flex-grow:${s.toFixed(2)};background:${hue};opacity:${[1, 0.72, 0.5][i % 3]}"></i>`); }
  return `<span class="nebars" title="${ta('Each bar is a shot - the wider, the longer it lasts')}">${out.join('')}</span>`;
};
function neStyle(box, ne) {
  const {st, OPT} = ne;
  const qs = [['where', t('Where was it filmed?'), OPT.where], ['type', t('Type of video'), OPT.types], ['rhythm', t('Rhythm'), OPT.rhythm],
              ['moods', t('Mood'), OPT.moods, OPT.max_moods], ['captions', t('Captions'), OPT.captions]];
  box.innerHTML = `<div class="nelab">${neIcon('i-sparkle', '--amber')}${t('A ready-made style')}</div>
    <div class="nepre">${OPT.presets.map(p => `<button class="nep${st.presets.includes(p.id) ? ' on' : ''}" data-p="${esc(p.id)}" title="${esc(t(p.help))}"><b>${esc(t(p.label))}</b>${neBars(p.rhythm)}</button>`).join('')}</div>
    <div class="neqs">${qs.map(([k, q, , max]) => `<div class="neqr"><label>${neIcon(...NE_Q[k])}${q}${max ? ` <span>${t('up to {n}', {n: max})}</span>` : ''}</label><div class="nechips" data-q="${k}"></div></div>`).join('')}
      <div class="neqr"><label for="newant">${neIcon('i-pen', '--amber')}${t('The feel in your words')}</label>
        <textarea id="newant" rows="1" placeholder="${ta('e.g. a hook in the first second, 3 s cuts, very fast paced, bold captions word by word, slow zooms while I talk')}">${esc(st.want)}</textarea></div></div>
    <div class="nelab nepalh"><span title="${ta('for titles, captions and graphics - none picked = Claude takes it from your clips and references')}">${neIcon('i-palette', '--pink')}${t('Colour palette')}</span><div class="nepal" id="nemine"></div></div>
    <div id="nepal"></div>`;
  qs.forEach(([k, , items, max]) => neChips($(`[data-q=${k}]`, box), items, st, k, {max, top: 4, auto: false, first: NE_FIRST[k], onChange: ne.changed}));
  $$('.nep', box).forEach(b => b.onclick = () => {
    const id = b.dataset.p; st.presets = st.presets.includes(id) ? st.presets.filter(x => x !== id) : [...st.presets, id];
    b.classList.toggle('on', st.presets.includes(id));
    const tk = OPT.presets.find(p => p.id === id);
    if (tk && tk.talk && st.presets.includes(id)) st.sound = 'talk';
    ne.changed(); });
  $('#newant', box).oninput = e => { st.want = e.target.value; ne.changed(); };
  nePalette($('#nepal', box), ne, $('#nemine', box));
}

// the palette: Auto or a ready-made one as big cards (a strip of its colours each) in box, the colours themselves as big
// swatches to change in mine, beside the palette's title (up to OPT.max_colours, the first = the main accent); none = Auto
function nePalette(box, ne, mine) {
  const {st, OPT} = ne;
  const same = cs => cs.length === st.palette.length && cs.every((c, i) => c.toUpperCase() === st.palette[i]);
  let mineB = [];                                        // My Brand's colours (step 3, 2026-10-26): the first card after Auto
  brandData().then(b => { mineB = brandPalette(b, OPT.max_colours); if (mineB.length) draw(); });
  const draw = () => {
    box.innerHTML = `<div class="nepals"><button class="nepl${st.palette.length ? '' : ' on'}" data-clear title="${ta('Auto - Claude picks')}"><span class="nestrip auto">${neIcon('i-sparkle')}</span><span>${t('Auto')}</span></button>
        ${mineB.length ? `<button class="nepl${same(mineB) ? ' on' : ''}" data-brandpal title="${ta('Your brand\'s colours, from My Brand')}"><span class="nestrip">${mineB.map(c => `<i style="background:${esc(c)}"></i>`).join('')}</span><span>${t('My Brand')}</span></button>` : ''}
        ${OPT.palettes.map(p => `<button class="nepl${same(p.colours) ? ' on' : ''}" data-p="${esc(p.id)}"><span class="nestrip">${p.colours.map(c => `<i style="background:${esc(c)}"></i>`).join('')}</span><span>${esc(t(p.label))}</span></button>`).join('')}</div>`;
    mine.innerHTML = `${st.palette.map((c, i) => `<span class="nesw"><input type="color" value="${esc(c.toLowerCase())}" data-i="${i}" title="${esc(c)}"><button class="nesx" data-x="${i}" title="${ta('Remove')}">✕</button></span>`).join('')}
        ${st.palette.length < OPT.max_colours ? `<button class="btn sm" data-add>${t('+ Add a colour')}</button>` : ''}`;
    $$('input[type=color]', mine).forEach(c => {
      c.oninput = () => { st.palette[+c.dataset.i] = c.value.toUpperCase(); ne.changed(); };
      c.onchange = draw; });
    $$('[data-x]', mine).forEach(b => b.onclick = () => { st.palette.splice(+b.dataset.x, 1); draw(); ne.changed(); });
    const add = $('[data-add]', mine);
    if (add) add.onclick = () => { st.palette.push(st.palette.length ? '#FFFFFF' : '#FF2D55'); draw(); ne.changed(); };
    const clear = $('[data-clear]', box);
    if (clear) clear.onclick = () => { st.palette = []; draw(); ne.changed(); };
    $$('[data-p]', box).forEach(b => b.onclick = () => { st.palette = OPT.palettes.find(p => p.id === b.dataset.p).colours.map(c => c.toUpperCase()); draw(); ne.changed(); });
    const bp = $('[data-brandpal]', box);
    if (bp) bp.onclick = () => { st.palette = [...mineB]; draw(); ne.changed(); };
  };
  draw();
}

// 5. Sound: the music as four cards (Auto, a song - the folder's or a downloaded one, picked under them -, the clips'
// own sound, talking), how many sound effects (a card each, with a strip of how often one plays) and which kinds
// (motionlab\sfx.py's cue kinds, grouped), notes. Its refresh = the songs again (one added, another video, a talking
// script picked).
function neSound(box, ne) {
  const {st, OPT} = ne;
  const MUSIC = [['auto', 'i-sparkle', t('Auto'), t("the folder's song, if any")], ['music', 'i-music', t('A song'), ''],
                 ['clips', 'i-film', t("The clips' own sound"), t('as filmed')], ['talk', 'i-mic', t('Talking'), t('pauses cut')]];
  const TICKS = {none: 0, few: 3, some: 6, many: 11};
  const amounts = [{id: '', label: t('Auto'), help: t('Claude decides')}, ...OPT.sfx_amount.map(x => ({id: x.id, label: t(x.label), help: t(x.help)}))];
  const strip = id => `<span class="netrk${id ? '' : ' auto'}">${Array.from({length: 12}, (_, i) =>
    `<i${id && Math.floor((i + 1) * TICKS[id] / 12) > Math.floor(i * TICKS[id] / 12) ? ' class="on"' : ''}></i>`).join('')}</span>`;
  box.innerHTML = `<div class="neq"><label>${neIcon('i-music', '--violet')}${t('Music')}</label>
      <div class="nemus">${MUSIC.map(([v, ic, l, s]) => `<button class="necard nemc" data-m="${v}" ${v === 'auto' ? `title="${ta('Automatic - the song in the folder if there is one')}"` : ''}><svg class="ic"><use href="#${ic}"/></svg><b>${l}</b><span data-ms="${v}">${s}</span></button>`).join('')}</div>
      <div class="nesongrow" id="nesongrow" hidden><select id="nesnd"></select>
        <label class="btn sm" id="nesong" title="${ta('Copies a song into this video - the original stays where it is')}"><svg class="i"><use href="#i-upload"/></svg>${t('Add a song…')}<input type="file" hidden accept="audio/*,.mp3,.m4a,.wav,.aac,.flac,.ogg"></label>
        <button class="btn sm" id="neslink" title="${ta('Downloads the song of a TikTok, YouTube or SoundCloud link as an MP3 - your edit cuts on its beats. To post, MotionLab also makes a copy without it: you add the same sound in TikTok or Instagram.')}"><svg class="i"><use href="#i-download"/></svg>${t('From a link…')}</button></div>
      <div class="nesongrow" id="nelinkrow" hidden><input type="text" id="nelinku" placeholder="${ta('Paste a link - TikTok, YouTube, SoundCloud…')}">
        <button class="btn sm pri" id="nelinkgo"><svg class="i"><use href="#i-download"/></svg>${t('Download')}</button><span class="small muted" id="nelinkst"></span><pre id="nelinklog" hidden></pre></div>
      <div class="nesongs" id="nesongs" hidden></div>
      <div id="nesongf"></div></div>
    <div class="neq" id="neambq"><label>${neIcon('i-volume', '--cyan')}${t('Ambience under your voice')} ${optTag(t('a quiet room, a café, a street - far under your words, it fills the silence between cuts'))}</label>
      <div class="neamb" id="neamb"></div></div>
    <div class="neq"><label>${neIcon('i-volume', '--amber')}${t('Sound effects')}</label>
      <div class="nesfx">${amounts.map(a => `<button class="necard nesfxc" data-a="${esc(a.id)}"><b>${esc(a.label)}</b><span>${esc(a.help)}</span>${strip(a.id)}</button>`).join('')}</div></div>
    <div class="neq" id="nekinds"><label>${neIcon('i-zap', '--pink')}${t('Which kinds')}</label><div class="nechips" data-q="kinds"></div><div class="nechelp" data-h="kinds"></div></div>
    <div class="neq" id="nepick"><label>${neIcon('i-volume', '--green')}${t('Choose the sounds')} ${optTag(t('a kind with sounds ticked uses only those'))}</label>
      <div class="row"><button class="btn sm" id="nepickb" aria-expanded="false"></button><span class="small muted">${t('Listen and tick the ones this video may use - your favourites from Motion Graphics > Sounds otherwise.')}</span></div>
      <div class="nepicks" id="nepicks" hidden></div></div>
    <div class="nef"><label for="nesnotes">${neIcon('i-pen', '--cyan')}${t('Notes on sound')}</label>
      <textarea id="nesnotes" rows="2" placeholder="${ta('e.g. a big hit when the logo appears, keep my voice clear over the music')}">${esc(st.snotes)}</textarea></div>`;
  const sel = $('#nesnd', box), songIn = $('#nesong input', box);
  let wantSong = false;                                     // "A song" clicked with no song yet: show where to get one
  const fill = () => {
    const songs = (ne.P() || {}).songs || [];
    sel.innerHTML = `${songs.length ? `<optgroup label="${ta("In this video's folder")}">${songs.map(s => `<option value="music:${esc(s)}">${esc(s)}</option>`).join('')}</optgroup>` : ''}
      ${OPT.songs.length ? `<optgroup label="${ta('Downloaded songs')}">${OPT.songs.map(s => `<option value="music:${esc(s.rel)}">${esc(s.name)}</option>`).join('')}</optgroup>` : ''}`;
    if (st.sound.startsWith('music:') && ![...sel.options].some(o => o.value === st.sound)) st.sound = sel.options.length ? sel.options[0].value : 'auto';
    const mode = st.sound.startsWith('music:') ? 'music' : st.sound;
    if (mode === 'music') sel.value = st.sound;
    $$('.nemc', box).forEach(b => b.classList.toggle('on', b.dataset.m === mode || (wantSong && b.dataset.m === 'music')));
    $('[data-ms=music]', box).textContent = mode === 'music' ? st.sound.slice(6).split('/').pop() : sel.options.length ? t('Pick a song') : t('Add a song…');
    $('#nesongrow', box).hidden = mode !== 'music' && !wantSong;
    sel.hidden = true;                                      // 0.6.0 step 10: the songs as cards (the select keeps the value)
    const cur = st.sound.startsWith('music:') ? st.sound.slice(6) : '', SG = $('#nesongs', box);
    SG.hidden = mode !== 'music' || !sel.options.length;
    SG.innerHTML = [...songs.map(x => ({v: x, title: x, folder: true})), ...OPT.songs.map(x => ({v: x.rel, ...x}))].map(x =>
      `<button type="button" class="btn necard nesong${cur === x.v ? ' on' : ''}" data-song="${esc(x.v)}">${x.folder ? `<svg class="i"><use href="#i-folder"/></svg>`
        : `<span class="btn sm ghost" data-mhear="${esc(x.v)}" role="button" title="${ta('Listen')}">${MU_PLAYING === x.v ? '❚❚' : '▶'}</span>`}
        <span class="grow"><b>${x.fav ? '★ ' : ''}${esc(x.title || x.name)}${x.artist ? ` <span class="muted small">${esc(x.artist)}</span>` : ''}</b>
        <span class="row">${x.folder ? `<span class="small dim">${t("In this video's folder")}</span>` : muChips(x)}</span></span></button>`).join('');
    $$('[data-song]', SG).forEach(b => b.onclick = e => { if (e.target.closest('[data-mhear]')) return; st.sound = 'music:' + b.dataset.song; ne.changed(); });
    const beds = OPT.beds || [], nk = {};
    $('#neambq', box).hidden = mode === 'music';
    if (st.ambience && !beds.some(x => x.rel === st.ambience)) st.ambience = '';
    $('#neamb', box).innerHTML = !beds.length ? `<span class="small muted">${t('No ambience yet - make some in Motion Graphics > Music.')}</span>`
      : [`<button type="button" class="fchip${!st.ambience ? ' on' : ''}" data-amb="">${t('None')}</button>`, ...beds.map(x => {
        nk[x.kind] = (nk[x.kind] || 0) + 1;
        const many = beds.filter(y => y.kind === x.kind).length > 1;
        return `<button type="button" class="fchip${st.ambience === x.rel ? ' on' : ''}" data-amb="${esc(x.rel)}" title="${esc(x.title)}"><span data-mhear="${esc(x.rel)}" role="button" title="${ta('Listen')}">${MU_PLAYING === x.rel ? '❚❚' : '▶'}</span>${esc(muBed(x.kind))}${many ? ' ' + nk[x.kind] : ''}${x.fav ? ' ★' : ''}</button>`; })].join('');
    $$('[data-amb]', box).forEach(b => b.onclick = e => { if (e.target.closest('[data-mhear]')) return; st.ambience = b.dataset.amb; ne.changed(); });
    $$('#nesongs [data-mhear], #neamb [data-mhear]', box).forEach(b => b.onclick = e => { e.stopPropagation(); muHear(b.dataset.mhear, b); });
    if ($('#nesongrow', box).hidden) $('#nelinkrow', box).hidden = true;
    $$('.nesfxc', box).forEach(b => b.classList.toggle('on', b.dataset.a === st.sfx));
    $('#nekinds', box).hidden = st.sfx === 'none';
    $('#nepick', box).hidden = st.sfx === 'none';
    $('#nepickb', box).textContent = (st.sounds || []).length ? tn(st.sounds.length, '{n} sound ticked', '{n} sounds ticked') : t('Pick the sounds…');
  };
  // 0.6.0 (step 9 b): the library's sounds in use, by kind - ▶ and a tick each (st.sounds = their files)
  let SDL = null, player = null;
  const picks = async () => {
    const P2 = $('#nepicks', box);
    if (!SDL) { P2.innerHTML = `<span class="small muted">${t('Loading…')}</span>`; try { SDL = (await api('/api/sounds')).sounds.filter(s => !s.off); } catch (e) { SDL = []; } }
    const kinds = [...new Set(SDL.map(s => s.kind))].sort((a, b) => edKind(a).localeCompare(edKind(b)));
    P2.innerHTML = !SDL.length ? `<span class="small muted">${t('No recorded sounds on this PC yet - add some in Motion Graphics > Sounds.')}</span>`
      : kinds.map(k => `<div class="nepk"><b class="small"><span class="eddot" style="--h:${meHue(k)}"></span>${esc(edKind(k))}</b>${SDL.filter(s => s.kind === k).map(s =>
        `<label class="nepks"><input type="checkbox" value="${esc(s.file)}"${(st.sounds || []).includes(s.file) ? ' checked' : ''}><button type="button" class="btn sm ghost" data-hear="${esc(s.file)}" title="${ta('Listen')}">▶</button><span>${esc(s.name)}${s.fav ? ' ★' : ''}</span></label>`).join('')}</div>`).join('');
    $$('[data-hear]', P2).forEach(b => b.onclick = e => { e.preventDefault(); try { if (player) player.pause(); player = new Audio(edSoundUrl(b.dataset.hear)); player.play().catch(() => {}); } catch (x) { /* no sound */ } });
    $$('input[type=checkbox]', P2).forEach(c => c.onchange = () => { st.sounds = $$('input[type=checkbox]:checked', P2).map(x => x.value); ne.changed(); });
  };
  $('#nepickb', box).onclick = () => { const P2 = $('#nepicks', box), b = $('#nepickb', box); P2.hidden = !P2.hidden; b.setAttribute('aria-expanded', String(!P2.hidden)); if (!P2.hidden) picks(); };
  $$('.nemc', box).forEach(b => b.onclick = () => { const m = b.dataset.m;
    wantSong = m === 'music' && !sel.options.length;
    if (m !== 'music') st.sound = m;
    else if (!st.sound.startsWith('music:') && sel.options.length) st.sound = sel.options[0].value;
    ne.changed(); });
  // a song from a link: the Analyser's downloader (yt-dlp, the MP3 preset -> refs\audio) as a job, then picked here
  $('#neslink', box).onclick = () => { const r = $('#nelinkrow', box); r.hidden = !r.hidden; if (!r.hidden) $('#nelinku', box).focus(); };
  $('#nelinku', box).onkeydown = e => { if (e.key === 'Enter') $('#nelinkgo', box).click(); };
  $('#nelinkgo', box).onclick = async () => {
    const url = $('#nelinku', box).value.trim(), go = $('#nelinkgo', box), msg = $('#nelinkst', box), pre = $('#nelinklog', box);
    if (!/^https?:\/\//i.test(url)) { toast(t('Paste a full link starting with https://'), 'err'); return; }
    const j = await startJob('download', {url, preset: 'mp3'}, false);
    if (!j) return;
    go.disabled = true; msg.textContent = t('downloading…'); pre.textContent = '';
    followJob(j.id, pre, done => {
      go.disabled = false;
      const file = pre.textContent.split('\n').map(l => l.trim()).reverse().find(l => FILE_RX.test(l));
      if (done.status !== 'done' || !file) { msg.innerHTML = esc(t(done.status)) + (done.status === 'failed' ? ' ' + reportBtn(done.id, 'sm ghost') : ''); return; }
      const name = file.split('\\').pop(), rel = 'refs/audio/' + name;
      if (!OPT.songs.some(s => s.rel === rel)) OPT.songs.push({name, rel});
      msg.textContent = t('done ✓'); $('#nelinku', box).value = ''; $('#nelinkrow', box).hidden = true;
      wantSong = false; st.sound = 'music:' + rel; ne.changed();
    });
  };
  sel.onchange = () => { st.sound = sel.value; ne.changed(); };
  songIn.onchange = async () => { const f = [...songIn.files]; songIn.value = '';
    await ne.addFiles(f, $('#nesongf', box));
    const songs = (ne.P() || {}).songs || [], s = f[0] && (songs.includes(f[0].name) ? f[0].name : songs[songs.length - 1]);
    if (s) { wantSong = false; st.sound = 'music:' + s; ne.changed(); } };
  $$('.nesfxc', box).forEach(b => b.onclick = () => { st.sfx = b.dataset.a; ne.changed(); });
  neChips($('[data-q=kinds]', box), OPT.sfx_kinds, st, 'kinds', {help: $('[data-h=kinds]', box), onChange: ne.changed});
  $('#nesnotes', box).oninput = e => { st.snotes = e.target.value; ne.changed(); };
  return fill;
}

// 6. Final: the length, the format (a card each, its shape drawn), then the summary - every step in one table, a click
// on one goes back to it - and Claude's time as one chip. Its refresh also sets the footer's two buttons (what they do
// = their tooltip; only a missing clip is said here).
function neFinal(box, ne) {
  const {st, OPT} = ne;
  const lens = [['', t('Auto')], ['15', '15 s'], ['30', '30 s'], ['45', '45 s'], ['60', '1 min'], ['90', '1:30 min']];
  const fmts = [['', t('Auto'), t("your clips' own shape")], ['vertical', t('Vertical 9:16'), 'TikTok · Reels · Shorts'],
                ['horizontal', t('Horizontal 16:9'), 'YouTube'], ['square', t('Square 1:1'), t('a feed post')]];
  box.innerHTML = `<div class="neq"><label>${neIcon('i-clock', '--cyan')}${t('Length')}</label><div class="nechips" id="nelen">${lens.map(([v, l]) => `<button class="nech" data-v="${v}">${l}</button>`).join('')}
      <input type="number" id="nelenx" min="3" max="900" step="1" placeholder="${ta('or seconds')}"></div></div>
    <div class="neq"><label>${neIcon('i-videos', '--violet')}${t('Format')}</label>
      <div class="nefmts">${fmts.map(([v, l, s]) => `<button class="necard nefmt" data-f="${v}"><i class="neshape ${v || 'auto'}"></i><span><b>${l}</b><span>${s}</span></span></button>`).join('')}</div></div>
    <div class="neq" id="neframeq"><label title="${ta('How a horizontal clip fills the vertical video')}">${neIcon('i-videos', '--pink')}${t('Framing')}</label>
      <div class="nefmts">${NE_FRAMES().map(([v, l, s]) => `<button class="necard nefmt" data-fr="${v}"><i class="nefri">${edFrameIcon(v || 'auto')}</i><span><b>${l}</b><span>${s}</span></span></button>`).join('')}</div></div>
    <div class="neq"><button class="necard nedvr" id="nedvr" title="${ta('the same edit as a timeline you can keep editing by hand')}"><span class="nedvlogo"><img src="/files/logos/davinci-resolve/color.svg" alt=""></span><b>${t('Build in DaVinci')}</b></button></div>
    <div class="neq"><label>${neIcon('i-clipboard', '--green')}${t('Summary')}</label><div class="nesum" id="nesumc"></div></div>
    <div class="nefinb"><span class="neest" id="neest"></span><span class="small amber" id="neneed"></span></div>`;
  const seg = $('#nelen', box), other = $('#nelenx', box);
  const paint = () => {
    $$('[data-v]', seg).forEach(b => b.classList.toggle('on', b.dataset.v === st.length));
    if (lens.some(([v]) => v === st.length)) other.value = '';
    $$('[data-f]', box).forEach(b => b.classList.toggle('on', b.dataset.f === st.format));
    $$('[data-fr]', box).forEach(b => b.classList.toggle('on', b.dataset.fr === st.framing));
    $('#neframeq', box).hidden = !neFramed(st);           // (0.6.1: only where a horizontal clip has to be framed)
    $('#nedvr', box).classList.toggle('on', !!st.resolve);
  };
  $$('[data-fr]', box).forEach(b => b.onclick = () => { st.framing = b.dataset.fr; paint(); ne.changed(); });
  // DaVinci Resolve (2026-10-25, the user: "move ... build it as a davinci project in the actual form in the final
  // section and make it more simple ... add the davinci logo, and just say 'build in davinci'"): one card, on / off
  $('#nedvr', box).onclick = () => { st.resolve = !st.resolve; paint(); ne.changed(); };
  $$('[data-v]', seg).forEach(b => b.onclick = () => { st.length = b.dataset.v; paint(); ne.changed(); });
  other.oninput = () => { const v = Math.round(+other.value); st.length = v >= 3 && v <= 900 ? String(v) : ''; paint(); ne.changed(); };
  $$('[data-f]', box).forEach(b => b.onclick = () => { st.format = b.dataset.f; paint(); ne.changed(); });
  paint();
  return () => {
    const R = neRows(ne), P = ne.P(), clips = !!(P && P.clips);
    $('#nesumc', box).innerHTML = NE_STEPS.map(([id, name, , ic, col]) => { const set = (R[id] || []).filter(r => !r.auto);
      return `<button class="nesumr${id === 'clips' && !clips ? ' need' : ''}" data-go="${id}">${neIcon(ic, col)}<span>${name}</span><span class="nesv">${set.length ? set.map(r => `<span title="${esc(r.k)}">${r.v}</span>`).join(' · ')
        : `<em>${id === 'clips' ? t('Pick your clips first') : t('Auto')}</em>`}</span></button>`; }).join('');
    $$('#nesumc [data-go]', box).forEach(b => b.onclick = () => ne.go(b.dataset.go));
    const m = st.length ? Math.round(+st.length * OPT.min_per_s) : 0, est = $('#neest', box);
    est.innerHTML = `<svg class="i"><use href="#i-clock"/></svg><span>${m ? t('About <b>{time}</b> of Claude', {time: m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${pad(m % 60)} min`})
      : t('Pick a length to see how long Claude may take')}</span>`;
    est.title = t('We count about {n} min of Claude per second of video.', {n: numStr(OPT.min_per_s)});
    const exactOk = !st.exact || st.like.length === 1;
    const look = brandOn(ne.el, '#nebrand') ? (((BRAND_DATA || {}).look || {}).like || []) : [];   // For my brand: its look
    const style = st.like.length || st.presets.length || st.want.trim() || st.rhythm || neTalk(st.prompt) || look.length;
    const go = $('#cvgo', ne.el), dr = $('#cvdraft', ne.el);
    go.disabled = !(clips && exactOk); dr.disabled = !(clips && !st.exact && style);
    go.title = !clips ? t('First your clips (1)') : ne.cur === NE_STEPS.length - 1                  // (on Segments, step 7)
      ? t("Claude picks the edit of the parts you left, writes the words on their cards and builds it - your picks stay, and you can change Claude's here afterwards")
      : t('Claude plans it with you, step by step');
    dr.title = st.exact ? t('An exact copy is made by Claude') : style || !clips
      ? t('A first version in a few minutes, by rules - no Claude. Watch it, then let Claude make it better.')
      : t('The quick draft needs a style: a reference (3), a rhythm or a ready-made style (4), or your words');
    $('#neneed', box).textContent = clips ? '' : t('First your clips (1)');
  };
}

// 7. Segments (0.6.1, docs\plans.md *Edit by segments* steps 5-6 - the user: "editar por segmentos" and "borrador (quick
// draft) select each segment how u would like it edited and then create the edit entirely"): the video cut into parts
// by the lab with these answers (the job `segments` = tools\segments.py --request: a bare quick draft - its cuts, sound,
// colour and framing, nothing on them - its parts and a picture of each), then a row per part: its picture, frame +
// timecode, its words, its edit (the rules' - why in one line - or the user's, *yours*), two others and the rest behind
// +N, *Preview* (that part alone with its edit, rendered: the job segments_preview, played in its picture), *Apply to all
// like this*; *Recommended for all* on top. Each pick = POST /api/project/<p>/segments (build\segment_picks.json, kept
// through a new cut). The footer's *Build the edit* = the job segments_build (every part as picked, checked, rendered).
// After Final, not after Text (the plan's first idea): the parts come from the draft's cuts, which need steps 3-6.
const SEG_T = () => ({plain: t('Plain'), punch: t('Punch-in'), broll: t('B-roll'), list: t('List'), number: t('Number'),
  title: t('Section title'), screen: t('Screen zoom'), graphic: t('Motion graphic'), beat: t('Beat cuts'), drop: t('Drop hit')});
const SEG_TIP = () => ({plain: ta('Nothing added - a breather between busier parts'),
  punch: ta("A step closer on the key word, back at the part's end"), broll: ta('A clip of yours over the talking, on the word it shows'),
  list: ta('What you count, as a list card'), number: ta('The number you say, counting up on a card'),
  title: ta("The part's first words as a title card"), screen: ta('A slow push into the screen recording'),
  graphic: ta('A Motion Graphics template that fits the words'), beat: ta('A cut on every beat, inside your clips'),
  drop: ta('A flash and a shake on the drop')});
const segWhy = w => esc(w && w[0] ? t(w[0], w[1] || {}) : '');          // (the tool's line, in the app's language)
// step 7: Claude's picks sit between the rules' and the user's - its why is its own line (the video's language, no
// key); the suggestion = Claude's pick where it made one, else the rules' (what *back to the suggestion* goes to)
const segWhyOf = s => s.by === 'claude' ? esc(s.why || '') : segWhy(s.why_k);
const segSug = s => s.claude || s.rule;
function segWho(s, reset) {                                             // whose pick, in one line
  const g = segSug(s), e = SEG_T()[g.t] || g.t;
  if (s.by === 'user') return `<span class="segyou">${t('yours')}</span> <button class="lnk" ${reset} title="${s.claude ? ta("Claude's pick for this part") : ta('The edit MotionLab suggests for this part')}">${t('back to the suggestion ({edit})', {edit: e})}</button>`;
  if (s.by === 'claude') return `<span class="clchip">${t("Claude's")}</span> <span class="muted">${segWhyOf(s)}</span>`;
  return `<span class="muted">${segWhyOf(s)}</span>`;
}
function segSay(s) {                                                    // its words; a song's bars, a montage's shots
  const m = s.kind === 'music' && /^bars? (\d+)(?:-(\d+))?$/.exec(s.say || '');
  if (m) return m[2] ? t('bars {a}-{b}', {a: m[1], b: m[2]}) : t('bar {a}', {a: m[1]});
  const k = s.kind === 'clips' && /^(\d+) shot/.exec(s.say || '');
  return k ? tn(+k[1], '{n} shot', '{n} shots') : s.say || '';
}
const segChip = (x, on, tip, data) => `<button class="segc t-${x}${on ? ' on' : ''}" ${data} title="${tip}"><i></i>${esc(SEG_T()[x] || x)}</button>`;
async function segWait(id, alive, ms = 1500) {                          // a job to its end -> its last status
  for (;;) {
    await new Promise(r => setTimeout(r, ms));
    if (!alive()) return null;
    let s; try { s = await api(`/api/jobs/${id}?since=999999`); } catch (e) { continue; }
    if (!['running', 'queued', 'cancelling'].includes(s.status)) return s;
  }
}
function neSegs(box, ne) {
  let S = null, cutting = false, busy = false;
  const more = new Set(), pv = {};                         // +N opened; parts whose preview is being made
  const P0 = () => ne.proj();
  const draw = () => {
    const P = ne.P(), b = $('#cvbuild', ne.el);
    if (b) b.disabled = !(S && S.segments.length) || cutting || busy;
    if (!P || !P.clips) { box.innerHTML = `<div class="nesegs0">${neIcon('i-videos', '--amber')}<b>${t('First your clips (1)')}</b></div>`; return; }
    if (cutting) { box.innerHTML = `<div class="nesegs0">${neIcon('i-restart', '--cyan')}<b>${t('Cutting your clips into parts…')}</b>
        <span class="small muted">${t('About a minute - the first time longer, while your words are written out.')}</span></div>`; return; }
    const ready = !$('#cvdraft', ne.el).disabled;           // (the quick draft's own rule: clips + a style)
    if (!S || !S.segments.length) {
      box.innerHTML = `<div class="nesegs0">${neIcon('i-film', '--cyan')}<b>${t('Choose how each part is edited')}</b>
        <span>${t("MotionLab cuts your clips with these answers and splits the video into parts - sentences, a song's phrases or runs of shots - with an edit suggested for each. Change any of them, then build the whole video in one go.")}</span>
        <button class="btn pri" id="nesegcut"${ready ? '' : ' disabled'}><svg class="i"><use href="#i-film"/></svg>${t('Cut it into parts')}</button>
        ${ready ? '' : `<span class="small amber">${esc($('#cvdraft', ne.el).title)}</span>`}</div>`;
      $('#nesegcut', box).onclick = cut;
      return;
    }
    const mine = S.segments.filter(s => s.by === 'user').length, cl = S.segments.filter(s => s.by === 'claude').length;
    box.innerHTML = `<div class="nesegtop"><b>${tn(S.segments.length, '{n} part', '{n} parts')}</b>${mine ? `<span class="small muted">${tn(mine, '{n} picked by you', '{n} picked by you')}</span>` : ''}
        ${cl ? `<span class="small muted">${tn(cl, '{n} picked by Claude', '{n} picked by Claude')}</span>` : ''}
        <span class="grow"></span><button class="btn sm ghost" id="nesegre"${ready ? '' : ' disabled'} title="${ta('Cut your clips again with the answers as they are now - your picks stay with their parts')}">${t('Cut it again')}</button>
        <button class="btn sm" id="nesegrec"${mine ? '' : ' disabled'} title="${S.claude ? ta("Every part back to the suggested edit - Claude's where it picked one") : ta('Every part back to the edit MotionLab suggests')}">${t('Recommended for all')}</button></div>
      ${S.picks_lost ? `<div class="small amber">${tn(S.picks_lost, '{n} of your picks is for a part this cut no longer has - it stays saved', '{n} of your picks are for parts this cut no longer has - they stay saved')}</div>` : ''}
      <div class="nesegl${busy ? ' busy' : ''}">${S.segments.map(row).join('')}</div>`;
    $('#nesegre', box).onclick = cut;
    $('#nesegrec', box).onclick = () => change({reset: 'all'});
    $$('[data-st]', box).forEach(c => c.onclick = () => { if (!c.classList.contains('on')) change({set: {[c.dataset.n]: c.dataset.st}}); });
    $$('[data-more]', box).forEach(c => c.onclick = () => { more.add(+c.dataset.more); draw(); });
    $$('[data-reset]', box).forEach(c => c.onclick = () => change({reset: c.dataset.reset}));
    $$('[data-like]', box).forEach(c => c.onclick = () => change({like: +c.dataset.like}));
    $$('[data-pv]', box).forEach(c => c.onclick = () => preview(+c.dataset.pv));
  };
  const row = s => {
    const TIP = SEG_TIP(), alts = s.alts.map(a => a.t), rest = s.can.filter(x => x !== s.pick && !alts.includes(x));
    const tip = x => x === s.pick ? segWhyOf(s) : esc(TIP[x] || '');
    const chips = [s.pick, ...alts, ...(more.has(s.n) ? rest : [])].map(x => segChip(x, x === s.pick, tip(x), `data-n="${s.n}" data-st="${x}"`)).join('')
      + (!more.has(s.n) && rest.length ? `<button class="segc more" data-more="${s.n}" title="${ta('Every edit this part can have')}">+${rest.length}</button>` : '');
    const pic = pv[s.n] ? `<span class="nesegw">${t('Rendering…')}</span>`
      : s.preview ? `<video src="${fileUrl(s.preview)}" controls playsinline preload="metadata"${s.still ? ` poster="${fileUrl(s.still)}"` : ''}></video>`
      : s.still ? `<img src="${fileUrl(s.still)}" alt="" loading="lazy">` : '';
    return `${s.topic ? `<div class="nesegtopic" title="${ta('Where Claude found the talk turning to a new point')}">${esc(s.topic)}</div>` : ''}<div class="neseg t-${s.pick}" data-n="${s.n}"><div class="nesegp">${pic}<span class="nesegn">${s.n}</span>
        ${s.preview || pv[s.n] ? '' : `<button class="nesegpv" data-pv="${s.n}" title="${ta('This part alone with its edit, rendered - about half a minute')}">▶ ${t('Preview')}</button>`}</div>
      <div class="nesegb"><div class="small muted">${frange(s.f0, s.f1, S.fps)} · ${dec((s.f1 - s.f0 + 1) / S.fps)} s</div>
        <div class="nesegs">${esc(segSay(s))}</div>
        <div class="nesegc">${chips}</div>
        <div class="nesegy small">${segWho(s, `data-reset="${s.n}"`)}
          ${s.text ? `<span class="nesegtx" title="${ta('The words Claude wrote for its card, or the word it lands on')}">“${esc(s.text.replace(/\|/g, ' / '))}”</span>` : ''}
          ${s.like.length ? ` · <button class="lnk" data-like="${s.n}" title="${ta('The parts MotionLab treated like this one get this edit too')}">${tn(s.like.length, 'Apply to all like this ({n} more)', 'Apply to all like this ({n} more)')}</button>` : ''}</div></div></div>`;
  };
  const load = async () => {
    const p = P0();
    if (!p) { S = null; draw(); return; }
    try { S = await api(`/api/project/${encodeURIComponent(p)}/segments`); } catch (e) { S = null; }
    draw(); ne.changed();
  };
  const change = async body => {
    if (busy || !S) return;
    busy = true; draw();
    try { S = await api(`/api/project/${encodeURIComponent(P0())}/segments`, {plan: S.plan, ...body}); } catch (e) { toast(e.message, 'err'); }
    busy = false; draw(); ne.changed();
  };
  async function cut() {                                   // the answers saved, then the job: a bare draft + its parts
    let j;
    try { await ne.save(); j = await api('/api/jobs', {kind: 'segments', args: {project: P0()}, queue: true}); }
    catch (e) { toast(e.message, 'err'); return; }
    cutting = true; more.clear(); draw();
    const s = await segWait(j.id, () => box.isConnected, 2000);
    cutting = false;
    if (s && s.status !== 'done') toast(t('The video could not be cut into parts.'), 'err');
    load();
  }
  async function preview(n) {
    let j;
    try { j = await api('/api/jobs', {kind: 'segments_preview', args: {project: P0(), plan: S.plan, n}, queue: true}); }
    catch (e) { toast(e.message, 'err'); return; }
    pv[n] = j.id; draw();
    const s = await segWait(j.id, () => box.isConnected);
    delete pv[n];
    if (s && s.status !== 'done') toast(t('Part {n} could not be previewed.', {n}), 'err');
    load();
  }
  ne.segEnter = () => { if (!cutting) load(); };
  ne.segs = () => S;
  draw();
  return () => { if (!cutting && !busy) { const b = $('#cvbuild', ne.el); if (b) b.disabled = !(S && S.segments.length); } };
}

// what was picked, per step: [{k: the question, v: the answer as html, s: a short plain answer for the steps on the left,
// auto}] - the steps and the summary both read it, so they never disagree
function neRows(ne) {
  const {st, OPT, PRM} = ne, P = ne.P();
  const lab = (list, id) => { const x = (list || []).find(o => o.id === id); return x ? t(x.label) : id; };
  const plain = v => String(v).replace(/<[^>]+>/g, '').replace(/&(amp|lt|gt|quot|#39);/g, (m, e) => ({amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'"}[e]));
  const row = (k, v, s = '', auto = false) => ({k, v, s: s || plain(v), auto});     // s goes in as text, v as html
  const pr = st.prompt && PRM.items.find(x => x.id === st.prompt);
  const names = st.like.map(k => { const v = ownVideos(ne.S).find(x => x.key === k); return v ? v.label || v.title || k : k; });
  const snd = st.sound.startsWith('music:') ? st.sound.slice(6).split('/').pop() : {auto: t('Automatic'), clips: t("The clips' own sound"), talk: t('Talking')}[st.sound];
  const lines = st.onscreen.split('\n').filter(x => x.trim());
  return {
    clips: P ? [row(t('Video'), esc(pname(P)), pname(P)), row(t('Clips'), P.clips ? plural(P.clips, 'clip') : `<span class="amber">${t('no clips yet')}</span>`)] : [],
    text: [st.about.trim() && row(t('What it is about'), esc(st.about.trim().slice(0, 140)) + (st.about.trim().length > 140 ? '…' : ''), t('notes')),
      lines.length && row(t('Text on screen'), lines.map(esc).join(' · '), plural(lines.length, 'line')),
      pr && row(t('Script or brief'), esc(pr.title || pr.title_auto || pr.id), t('a script')),
      (st.products || []).length && row(t('Products'), st.products.map(x => esc((((BRAND_DATA || {}).catalogue || []).find(p => p.id === x.id) || {}).name || x.id)
        + ` <span class="muted">(${{passing: t('In passing'), end: t('At the end'), both: t('Both')}[x.how]})</span>`).join(', '), tn(st.products.length, '{n} product', '{n} products'))].filter(Boolean),
    refs: [st.like.length && row(st.exact ? t('An exact copy of') : t('In the style of'), names.map(esc).join(', '), plural(st.like.length, 'video'))].filter(Boolean),
    style: [st.where && row(t('Filmed'), lab(OPT.where, st.where)), st.type && row(t('Type of video'), lab(OPT.types, st.type)),
      st.rhythm && row(t('Rhythm'), lab(OPT.rhythm, st.rhythm)), st.moods.length && row(t('Mood'), st.moods.map(m => lab(OPT.moods, m)).join(', ')),
      st.captions && row(t('Captions'), lab(OPT.captions, st.captions)),
      st.presets.length && row(t('Ready-made'), st.presets.map(p => lab(OPT.presets, p)).join(', ')),
      st.want.trim() && row(t('In your words'), esc(st.want.trim().slice(0, 140)), t('your words')),
      st.palette.length && row(t('Palette'), st.palette.map(c => `<i class="nedot" style="background:${esc(c)}"></i>`).join(''), plural(st.palette.length, 'colour'))].filter(Boolean),
    sound: [row(t('Music'), esc(snd), '', st.sound === 'auto'), row(t('Sound effects'), st.sfx ? lab(OPT.sfx_amount, st.sfx) : t('Auto'), '', !st.sfx),
      st.ambience && !st.sound.startsWith('music:') && row(t('Ambience'), esc(muBed(((OPT.beds || []).find(x => x.rel === st.ambience) || {}).kind || ''))),
      st.kinds.length && st.sfx !== 'none' && row(t('Kinds'), st.kinds.map(k => lab(OPT.sfx_kinds, k)).join(', ')),
      (st.sounds || []).length && st.sfx !== 'none' && row(t('Sounds'), tn(st.sounds.length, '{n} picked', '{n} picked')),
      st.snotes.trim() && row(t('Notes'), esc(st.snotes.trim().slice(0, 140)), t('notes'))].filter(Boolean),
    final: [row(t('Length'), st.length ? `${st.length} s` : t('Auto'), '', !st.length),
      row(t('Format'), st.format ? {vertical: t('Vertical 9:16'), horizontal: t('Horizontal 16:9'), square: t('Square 1:1')}[st.format] : t('Auto'), '', !st.format),
      neFramed(st) && st.framing && row(t('Framing'), (NE_FRAMES().find(([v]) => v === st.framing) || [0, st.framing])[1]),
      st.resolve && row('DaVinci Resolve', t('yes, a project too'))].filter(Boolean),
    segs: (Sg => Sg && Sg.segments.length ? [row(t('Parts'), tn(Sg.segments.length, '{n} part', '{n} parts')),
      Sg.segments.some(s => s.by === 'user') && row(t('Yours'), tn(Sg.segments.filter(s => s.by === 'user').length, '{n} picked by you', '{n} picked by you')),
      Sg.segments.some(s => s.by === 'claude') && row('Claude', tn(Sg.segments.filter(s => s.by === 'claude').length, '{n} picked by Claude', '{n} picked by Claude'))].filter(Boolean)
      : [])(ne.segs && ne.segs())};
}
// 0.6.1 (vertical framing, step 5): how a horizontal clip fills a vertical (or square) video - Auto = per shot
const NE_FRAMES = () => [['', t('Auto'), t('picked per shot')], ['fill', t('Fill'), t('the face fills the frame')],
  ['fit', t('Fit'), t('all of the picture in a band')], ['split', t('Split'), t('two people, one above the other')]];
const neFramed = st => st.format === 'vertical' || st.format === 'square';
// the steps on the left: before the one on screen = a tick and the short answer (Auto when nothing was picked), the one
// on screen = a gold ring and Now, the rest their number (dashed = optional) and their answer once something is picked;
// red = no clips; .rchn = the line down to the next step is gold (that step is reached)
function neNav(el, ne) {
  const R = neRows(ne), clips = !!(ne.P() || {}).clips;
  $$('.nenav button', el).forEach((b, i) => {
    const id = b.dataset.go, s = (R[id] || []).filter(r => !r.auto).map(r => r.s), on = i === ne.cur, need = id === 'clips' && !clips && !on, done = i < ne.cur && !need;
    b.classList.toggle('on', on); b.classList.toggle('done', done); b.classList.toggle('need', need); b.classList.toggle('rchn', i < ne.cur);
    $('b', b).textContent = done ? '✓' : i + 1;
    $('small', b).textContent = on ? t('Now|step') : need ? t('pick your clips') : s.length ? s.slice(0, 3).join(' · ') : done ? t('Auto') : '';
  });
}

const neBody = st => ({like: st.like, exact: st.exact, prompt: st.prompt, about: st.about, on_screen: st.onscreen, presets: st.presets, want: st.want,
  style: {where: st.where, type: st.type, rhythm: st.rhythm, moods: st.moods, captions: st.captions, palette: st.palette},
  sfx: {amount: st.sfx, kinds: st.kinds, notes: st.snotes, sounds: st.sounds || []}, length_s: st.length || null, format: st.format || null,
  music: st.sound.startsWith('music:') ? st.sound.slice(6) : '', sound: st.sound.startsWith('music:') ? 'music' : st.sound, resolve: st.resolve,
  ambience: st.sound.startsWith('music:') ? '' : st.ambience || '', photos: st.photos || {}, products: st.products || [],
  framing: neFramed(st) && st.framing ? st.framing : null});
