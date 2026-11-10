/* MotionLab app - js/editor.js: the Editor (projEditor): the timeline, captions, graphics, sounds, keyframes.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';

// a graphic's name on the timeline: its first words, else its template's name, else its folder without the prefixes
function edGfxName(g, S, lib) {
  if (g.captions) return t('Captions');
  const w = (g.words || []).find(x => x.value && String(x.value).trim());
  if (w) return String(w.value).replace(/\*/g, '').slice(0, 40);
  const fo = (S.folders || {})[g.dir] || {}, T = fo.from && (lib || []).find(x => x.id === fo.from);
  return T ? t(T.name) : String(g.folder || g.id).replace(/^(v\d+_|n\d+_)?(g|d)?\d+_/, '').replace(/_m\d+$/, '').replace(/[-_]/g, ' ');
}

function projEditor(el, P) {
  const enc = encodeURIComponent(P.name);
  el.innerHTML = `<div class="ed">
    <div class="edtop"><div id="edpick"></div><div class="edtitle" id="edtitle"></div><div class="grow"></div>
      <button class="btn sm ghost edswap" id="edswap" title="${ta('Swap the side panels - drag their inner edges to make them wider or narrower')}" aria-label="${ta('Swap the side panels')}">⇄</button>
      <button class="btn sm ghost" id="edundo" title="${ta('Undo (Ctrl+Z)')}" disabled>↶ ${t('Undo')}</button>
      <button class="btn sm ghost" id="edredo" title="${ta('Redo (Ctrl+Shift+Z)')}" disabled>↷ ${t('Redo')}</button>
      <span class="edhw"><button class="btn sm ghost" id="edhist" disabled aria-haspopup="true" aria-expanded="false" title="${ta('What you changed, in order')}"></button><div class="edpop" id="edpop" hidden></div></span>
      <button class="btn pri edsave" id="edsave" disabled><svg class="i"><use href="#i-edit"/></svg>${t('Save as a new version')}</button></div>
    <div class="edmain" id="edmain">
      <aside class="edpanel edl"><div class="edpin edadd" id="edadd"></div><div class="edvsplit" data-side="l" role="separator" aria-orientation="vertical" title="${ta('Drag to make this panel wider or narrower - double-click: as it was')}"></div></aside>
      <div class="edview"><div id="edprev"></div><div class="edrng" id="edrng" hidden></div>
        <div class="edtrans"><button class="btn sm" data-tr="start" title="${ta('First frame (Home)')}">⏮</button><button class="btn sm" data-tr="-1" title="${ta('1 frame back (←)')}">◀</button>
          <button class="btn edplay" data-tr="play" title="${ta('Play / pause (Space)')}">▶</button><button class="btn sm" data-tr="1" title="${ta('1 frame on (→)')}">▶</button><button class="btn sm" data-tr="end" title="${ta('Last frame (End)')}">⏭</button>
          <span class="edtime mono" id="edtime"></span><button class="btn sm ghost" data-tr="mute" title="${ta('Sound on / off (M)')}">🔊</button>
          <input type="range" class="edvol" id="edpvol" min="0" max="100" step="1" value="${Math.round(Math.sqrt(edVolume()) * 100)}" title="${ta('Preview volume - how loud you hear it here; the video itself does not change')}" aria-label="${ta('Preview volume')}">
          <select id="edsafe" class="edsafesel" hidden title="${ta('Where TikTok, Reels and Shorts put their own buttons, name and caption - keep words and faces inside the dashed box')}"></select></div></div>
      <aside class="edpanel edr"><div class="edpin edinsp" id="edinsp"></div><div class="edvsplit" data-side="r" role="separator" aria-orientation="vertical" title="${ta('Drag to make this panel wider or narrower - double-click: as it was')}"></div></aside></div>
    <div class="edsplitter" id="edsplitter" role="separator" aria-orientation="horizontal" title="${ta('Drag to make the preview bigger or smaller - double-click: as it was')}"></div>
    <div class="edtl" id="edtl"><div class="edtools">
        <button class="btn sm" id="edsplit" title="${ta('Split the shot under the playhead (S)')}">✂ ${t('Split')}</button>
        <button class="btn sm" id="eddel" title="${ta('Delete what is selected (Delete)')}" disabled><svg class="i"><use href="#i-trash"/></svg>${t('Delete')}</button>
        <button class="btn sm" id="edcapadd" hidden title="${ta('A new caption at the playhead - then type its words')}">＋ ${t('Caption')}</button>
        <span class="edsep"></span>
        <button class="btn sm ghost on" id="edsnap" title="${ta('Snap to cuts, the playhead and the other items')}">🧲 ${t('Snap')}</button>
        <button class="btn sm ghost" id="edrange" title="${ta('The two seconds around the playhead with your changes, rendered exactly as Save will (picture only)')}"><svg class="i"><use href="#i-film"/></svg>${t('See it rendered')}</button>
        <span class="grow"></span><span class="small muted" id="edhint"></span>
        <button class="btn sm ghost" id="edzo" title="${ta('Zoom out (-)')}">−</button><input type="range" id="edzoom" min="0" max="100" value="0" title="${ta('Zoom (Ctrl + wheel)')}"><button class="btn sm ghost" id="edzi" title="${ta('Zoom in (+)')}">+</button></div>
      <div class="edtlbody"><div class="edheads" id="edheads"></div><div class="edscroll" id="edscroll"><div class="edcanvas" id="edcanvas"></div></div></div></div>
  </div>`;
  document.body.classList.add('edwide');                     // (the user, 2026-10-27: the page's padding off - more room)
  let plan = '', base = null, cur = null, ops = [], labels = [], redo = [], sel = null, busy = false, pv = null, saving = false;
  let pxf = 1, zoom = 0, snap = true, lib = [], mediaJob = null, prevF = 0, capFocus = false;
  let segs = null;                                           // 0.6.1: an edit by segments' parts (its lane), or null
  let lineEdit = null;                                       // 2026-11-03: the shot whose line is being corrected
  const fps = () => (cur || base).fps;
  const tcf = f => `f${f} (${tc(f, fps())})`;
  const store = () => `ml.editor.${P.name}.${plan}`;
  const planSig = B => `${B.frames}:${B.shots.map(x => `${x.id}@${x.start}-${x.end}`).join(',')}:${B.graphics.length}:${B.sfx.length}`;
  const keep = () => { try { if (ops.length) localStorage.setItem(store(), JSON.stringify({ops, labels, sig: planSig(base)})); else localStorage.removeItem(store()); } catch (e) { /* private window */ } };
  const capEdits = () => (cur || base).capedits || {};     // the captions' new words / frames per folder (the engine's)
  // ---------------------------------------------------------------- loading a version
  let loadNo = 0, gone = false;
  const load = r => loadPlan(planOfRender(P, r).file);
  const loadPlan = async pf => {
    const my = ++loadNo;
    if (pv) { pv.destroy(); pv = null; }
    if (!pf) { $('#edprev', el).innerHTML = `<div class="empty">${t('This render has no plan - the Editor changes a version MotionLab made.')}</div>`; return; }
    $('#edprev', el).innerHTML = `<div class="empty">${t('Loading…')}</div>`;
    let st;
    try { st = await api(`/api/project/${enc}/miniedit?plan=${encodeURIComponent(pf)}`); }
    catch (e) { if (my === loadNo && !gone) $('#edprev', el).innerHTML = `<div class="empty bad">${t('The Editor could not open this version: {err}', {err: esc(e.message)})}</div>`; return; }
    if (my !== loadNo || gone) return;                       // another version was picked meanwhile, or the tab left
    try { await opened(pf, st, my); }
    catch (e) {
      if (pv) { pv.destroy(); pv = null; }
      $('#edprev', el).innerHTML = `<div class="empty bad">${t('The Editor could not open this version: {err}', {err: esc(e.message)})}</div>`;
      try { localStorage.removeItem(`ml.editor.${P.name}.${pf}`); } catch (x) { /* private window */ }
      console.error(e);
    }
  };
  // the preview's options (made again when its light copies arrive); 0.6.1: the selected shot's crop dragged on it
  const pvOpts = () => ({fps: base.fps, W: base.width, H: base.height, media: base.media,
    onFrame: f => { prevF = f; paintHead(); }, onPlay: on => { const b = $('[data-tr=play]', el); if (b) b.textContent = on ? '❚❚' : '▶'; },
    dragFor: f => { const s = sel && sel.k === 'shot' && !saving && cur && cur.shots.find(x => x.id === sel.id);
      return s && s.frame && !s.frame.shake && f >= s.start && f <= s.end ? s.id : null; },
    onCrop: c => { const s = cur.shots.find(x => x.id === c.shot);
      push({op: 'frame', shot: c.shot, x: +c.x.toFixed(4), ...(c.y == null ? {} : {y: +c.y.toFixed(4)}), ...(c.panel ? {panel: c.panel} : {})},
        t('Shot {n}: its crop moved', {n: s ? s.n : '?'})); }});
  const opened = async (pf, st, my) => {
    base = st; plan = pf; cur = base; ops = []; labels = []; redo = []; sel = null; segs = null;
    try { const Sg = await api(`/api/project/${enc}/segments?plan=${encodeURIComponent(pf)}`);    // (a bare draft or
      if (my !== loadNo || gone) return;                                                         // a version built
      segs = Sg.segments && Sg.segments.length ? Sg : null; } catch (e) { segs = null; }         // from its parts)
    $('#edtitle', el).innerHTML = `<span class="small muted">${t('{w}×{h} · {fps} fps', {w: base.width, h: base.height, fps: base.fps})}</span>`;
    pv = new EdPreview($('#edprev', el), pvOpts());
    let back = null;
    try { back = JSON.parse(localStorage.getItem(store()) || 'null'); } catch (e) { back = null; }
    if (back && back.ops && back.ops.length && back.sig && back.sig !== planSig(base)) back = null;   // the plan changed since
    if (back && back.job && back.ops && back.ops.length) {    // sent with Save (2026-11-10): unsaved again only when
      let j = null;                                           // that job never made its version
      try { j = await api(`/api/jobs/${back.job}?since=999999`); } catch (e) { j = null; }   // (job numbers start again
      if (my !== loadNo || gone) return;                                                     // with the server: its
      const st = j && j.kind === 'miniedit' && j.args && j.args.changes === back.ch ? j.status : 'gone';   // changes file)
      const vn = p => +String((p || {}).version || '').replace(/\D/g, '') || 0;                   // "v12" -> 12
      const v0 = vn(P.plans.find(p => p.file === plan));
      if (st === 'running' || st === 'queued' || st === 'cancelling') back = null;                // still being saved
      else if (st === 'done' || (st === 'gone' && P.plans.some(p => vn(p) > v0))) {               // saved: forget them
        back = null; try { localStorage.removeItem(store()); } catch (x) { /* private window */ } }
    }
    if (back && back.ops && back.ops.length) {
      try { const S2 = await api(`/api/project/${enc}/miniedit/preview`, {plan, ops: back.ops});
        if (my !== loadNo || gone) return;
        cur = S2; ops = back.ops; labels = back.labels || back.ops.map(o => o.op);
        toast(t('Your unsaved changes are back.'), 'ok'); }
      catch (e) { cur = base; try { localStorage.removeItem(store()); } catch (x) { /* */ } }
    }
    pv.setState(cur, capEdits()); applySafe();
    draw();
    media();
  };
  // the preview's light copies of the clips: made once (a job of seconds), the preview uses the clips meanwhile
  const media = async () => {                               // (the other clips of the video: made quietly after)
    if (!(base.need_media || base.need_more) || mediaJob) return;
    const quiet = !base.need_media;
    if (!quiet) pv.wait(`<span>${t('Getting your clips ready for the preview…')}</span>`);
    try { mediaJob = (await api(`/api/project/${enc}/editor/media`, {plan})).id; } catch (e) { pv.wait(''); return; }
    const tick = async () => {
      if (gone) return;
      let j; try { j = await api(`/api/jobs/${mediaJob}?since=999999`); } catch (e) { setTimeout(tick, 1500); return; }
      if (['running', 'queued', 'cancelling'].includes(j.status)) { setTimeout(tick, 800); return; }
      mediaJob = null;
      if (!pv || gone) return;
      if (j.status !== 'done') { if (quiet) return; pv.wait(`<span>${t('The preview copies could not be made - the preview plays your clips as they are.')}</span>`); setTimeout(() => pv && pv.wait(''), 6000); return; }
      try { const fresh = await api(`/api/project/${enc}/miniedit?plan=${encodeURIComponent(plan)}`); base.media = fresh.media; base.need_media = base.need_more = false; } catch (e) { /* keep */ }
      if (quiet && pv.playing) return;                       // (never in the middle of playing: the next load has them)
      const f = pv.f, D = pv.box; pv.destroy();
      pv = new EdPreview(D, pvOpts());
      pv.setState(cur, capEdits()); applySafe(); pv.seek(f); drawTL();
    };
    tick();
  };
  // ---------------------------------------------------------------- a change = a step, the timeline as it would be
  const preview = async (nops, nlabels, keepRedo = false) => {
    if (busy) return false;
    busy = true; el.classList.add('edbusy');
    try {
      const S = nops.length ? await api(`/api/project/${enc}/miniedit/preview`, {plan, ops: nops}) : base;
      cur = S; ops = nops; labels = nlabels; if (!keepRedo) redo = [];
      keep(); return true;
    } catch (e) { toast(e.message, 'err'); return false; }
    finally { busy = false; el.classList.remove('edbusy'); if (pv && cur) pv.setState(cur, capEdits()); draw(); }
  };
  const push = (op, label, after) => preview([...ops, op], [...labels, label]).then(ok => { if (ok && after) { after(); draw(); } return ok; });
  const settle = async () => {                               // the field being typed in gives its change first
    const a = document.activeElement;
    if (a && el.contains(a) && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)) { a.blur(); await new Promise(r => setTimeout(r, 0)); }
    for (let i = 0; busy && i < 200; i++) await new Promise(r => setTimeout(r, 50));
  };
  const undo = async () => { await settle(); if (!ops.length || busy) return; const o = ops[ops.length - 1], l = labels[labels.length - 1];
    preview(ops.slice(0, -1), labels.slice(0, -1), true).then(ok => { if (ok) { redo.push([o, l]); sel = null; draw(); } }); };
  const redoIt = async () => { await settle(); if (!redo.length || busy) return; const [o, l] = redo[redo.length - 1];
    preview([...ops, o], [...labels, l], true).then(ok => { if (ok) { redo.pop(); draw(); } }); };
  // ---------------------------------------------------------------- the timeline
  const shotAt = f => cur.shots.find(s => s.start <= f && f <= s.end);
  const sfxOf = q => `${q.f}|${q.kind}`;
  function rows() {                                          // graphics on lanes: one row each where they overlap in time
    const G = cur.graphics.filter(g => !g.captions && !g.scene).sort((a, b) => a.start - b.start), end = [], row = new Map();
    G.forEach(g => { let r = end.findIndex(e => e < g.start); if (r < 0) r = end.length; end[r] = g.end; row.set(g.id, r); });
    return {G, row, n: Math.max(1, end.length)};
  }
  function sfxRows() {                                       // sound effects on rows where they would overlap
    const end = [], row = [], px = Math.max(1e-6, pxf);
    cur.sfx.forEach((q, i) => { const a = q.f, b = q.f + Math.max(18 / px, (q.len_s || 0.3) * cur.fps);
      let r = end.findIndex(e => e <= a); if (r < 0) r = end.length; end[r] = b; row[i] = r; });
    return {row, n: Math.max(1, Math.min(3, end.length))};
  }
  function fxRows() {                                        // effect chips on rows where they overlap
    const end = [], row = new Map();
    (cur.effects || []).forEach(x => { const a = x.f, b = x.f + Math.max(x.len, 84 / Math.max(1e-6, pxf));   // (its name beside it)
      let r = end.findIndex(e => e <= a); if (r < 0) r = end.length; end[r] = b; row.set(x.id, r); });
    return {row, n: Math.max(1, Math.min(3, end.length))};
  }
  function lanes() {
    const R = rows(), Q = sfxRows(), F = fxRows(), y = {};
    let Y = ED_ROW.ruler;
    if (segs) { y.seg = Y; Y += ED_ROW.seg; }
    if (cur.captions.length || capPieces().length) { y.cap = Y; Y += ED_ROW.cap; }
    y.gfx = Y; Y += R.n * ED_ROW.gfx;
    if (cur.shots.length) { y.shot = Y; Y += ED_ROW.shot; }
    if (cur.shots.length || (cur.effects || []).length) { y.fx = Y; Y += F.n * ED_ROW.fx; }
    y.sfx = Y; Y += Q.n * ED_ROW.sfx;
    y.wave = Y; Y += ED_ROW.wave;
    return {R, Q, F, y, H: Y + 6};
  }
  // ---------------------------------------------------------------- keyframes and transitions on the main track
  const drawOf = id => (cur.draw || []).find(d => d.id === id && d.t === 'clip');
  function keyFramesOf(s) {                                  // a shot's diamonds: every key on it, merged by frame
    const d = drawOf(s.id), fs = new Set();
    if (d) ED_KEY_PROPS().forEach(([p]) => (edKKeys(d, p) || []).forEach(k => { if (k[0] >= s.start && k[0] <= s.end) fs.add(k[0]); }));
    return [...fs].sort((a, b) => a - b);
  }
  const keyShot = () => sel && (sel.k === 'shot' || sel.k === 'key') ? cur.shots.find(s => s.id === sel.id && !s.scene) : null;
  const plainCuts = () => { const S = cur || base; return S.shots.slice(1).filter((s, i) => !s.scene && !S.shots[i].scene && s.start === S.shots[i].end + 1); };
  const nearCut = f => { const C = plainCuts(); return C.length ? C.reduce((a, b) => (Math.abs(b.start - f) < Math.abs(a.start - f) ? b : a)) : null; };
  function trackExtras(y) {
    const S = cur, on = test => (test ? ' on' : ''), has = new Set((S.transitions || []).map(x => x.shot));
    const tr = (S.transitions || []).map(x => `<div class="edit edtr${on(sel && sel.k === 'tr' && sel.id === x.shot)}${x.frozen ? ' frozen' : ''}" data-k="tr" data-id="${esc(x.shot)}"
        style="left:${(x.f * pxf).toFixed(1)}px;width:${Math.max(16, x.len * pxf).toFixed(1)}px;top:${y.shot + 9}px;height:${ED_ROW.shot - 24}px"
        title="${esc(edTrLabel(x.label))} · ${esc(tcf(x.f))} - ${esc(tcf(x.f + x.len - 1))}${x.frozen ? ' · ' + ta('{n} frames hold still', {n: x.frozen}) : ''}"><span>${ED_TR_ICON[x.kind] || '◐'}</span><i class="edh l"></i><i class="edh r"></i></div>`).join('');
    const cuts = saving ? '' : plainCuts().filter(s => !has.has(s.id)).map(s => `<button class="edcutb" data-cut="${esc(s.id)}" style="left:${(s.start * pxf).toFixed(1)}px;top:${y.shot + ED_ROW.shot / 2 - 12}px" title="${ta('Add a transition on this cut')}">+</button>`).join('');
    const ks = keyShot();
    const kf = ks ? keyFramesOf(ks).map(f => `<div class="edit edkf${on(sel.k === 'key' && sel.f === f)}" data-k="key" data-s="${esc(ks.id)}" data-f="${f}"
        style="left:${(f * pxf).toFixed(1)}px;top:${y.shot + ED_ROW.shot - 18}px" title="${ta('A keyframe - drag it to another moment, click it for its ease')} · ${esc(tcf(f))}"></div>`).join('') : '';
    return tr + cuts + kf;
  }
  const rulerStep = () => [1, 2, 5, 10, 15, 30, 60, 120].find(s => s * fps() * pxf >= 64) || 300;
  const sLabel = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  function thumbRel(src) { const m = base.media[src] || {}; return m.proxy || m.source || m.photo || ''; }
  function drawTL() {
    if (!cur) return;
    const S = cur, N = S.frames, sc = $('#edscroll', el), cw = Math.max(300, sc.clientWidth - 32);   // (fit: no scrollbar)
    const fit = cw / N;
    pxf = fit * Math.pow(Math.max(1, 14 / fit), zoom / 100);
    const W = Math.ceil(N * pxf) + 24, {R, Q, F, y, H} = lanes(), on = (k, test) => sel && sel.k === k && test ? ' on' : '';
    const step = rulerStep(), ticks = [];
    for (let s = 0; s * fps() < N; s += step) ticks.push(`<span class="edtick" style="left:${(s * fps() * pxf).toFixed(1)}px">${sLabel(s)}</span>`);
    const lock = S.timing_locked;
    const shotHtml = s => {
      const w = (s.end - s.start + 1) * pxf, m = base.media[s.src] || {}, st = m.strip, flat = {...s, jumps: null, hold: false};
      let pics;
      const sth = s.scene && (S.folders[s.scene] || {}).thumb;
      if (s.scene) pics = `<div class="edpics scene"${sth ? ` style="--th:url('${fileUrl(sth)}')"` : ''}></div>`;   // a scene: its graphic
      else if (st && st.url) {                               // the clip's filmstrip (one picture, its cells by CSS)
        const th = ED_ROW.shot - 8, tw = th * st.tw / st.th, n = Math.min(400, Math.ceil(w / tw));
        pics = `<div class="edpics strip" style="--strip:url('${fileUrl(st.url)}');--bs:${(st.cols * tw).toFixed(1)}px ${(st.rows * th).toFixed(1)}px">${Array.from({length: n}, (_, i) => {
          const k = clamp(Math.floor(edSrcAt(flat, Math.min(s.end, s.start + (i + 0.5) * tw / pxf)) / S.fps / st.every), 0, st.n - 1);
          return `<i style="width:${tw.toFixed(1)}px;background-position:${(-(k % st.cols) * tw).toFixed(1)}px ${(-Math.floor(k / st.cols) * th).toFixed(1)}px"></i>`; }).join('')}</div>`;
      } else {                                               // until it is made: one picture of the shot
        const tr = thumbRel(s.src), mid = edSrcAt(flat, Math.floor((s.start + s.end) / 2));
        pics = `<div class="edpics">${tr ? `<img src="/api/thumb?video=${encodeURIComponent(tr)}&f=${Math.round(mid / S.fps) * S.fps}&fps=${S.fps}" loading="lazy" alt="" draggable="false">` : ''}</div>`;
      }
      return `<div class="edit edshot${on('shot', sel && sel.id === s.id)}${lock ? ' locked' : ''}${s.scene ? ' scene' : ''}" data-k="shot" data-id="${esc(s.id)}" style="left:${(s.start * pxf).toFixed(1)}px;width:${w.toFixed(1)}px;top:${y.shot}px;height:${ED_ROW.shot - 6}px"
        title="${esc(s.scene ? `${t('Scene {n}', {n: s.n})} · ${edGfxName(S.graphics.find(g => g.id === s.id) || {id: s.id}, S, lib)}` : t('Shot {n}', {n: s.n}))} · ${esc(tcf(s.start))} - ${esc(tcf(s.end))}${((((S.lines || {})[s.id] || {}).say || {}).what) ? `\n${esc(S.lines[s.id].say.what)}` : ''}">${pics}
        <span class="edlab">${s.n} · ${dec((s.end - s.start + 1) / S.fps)} s</span>${s.speed !== 1 ? `<span class="edspd">${numLoc(s.speed)}×</span>` : ''}
        ${lock ? '' : '<i class="edh l"></i><i class="edh r"></i>'}</div>`;
    };
    $('#edcanvas', el).style.width = `${W}px`; $('#edcanvas', el).style.height = `${H}px`;
    const built = segs && segs.built ? segs.built.picks : null, ST = SEG_T();
    $('#edcanvas', el).innerHTML = `<div class="edruler" style="height:${ED_ROW.ruler}px">${ticks.join('')}</div>
      ${y.seg != null ? segs.segments.map(s => `<div class="edit edseg t-${s.pick}${on('seg', sel && sel.id === s.n)}${built && built[s.n] && built[s.n] !== s.pick ? ' changed' : ''}" data-k="seg" data-n="${s.n}"
          style="left:${(s.f0 * pxf).toFixed(1)}px;width:${Math.max(6, (s.f1 - s.f0 + 1) * pxf).toFixed(1)}px;top:${y.seg}px;height:${ED_ROW.seg - 5}px"
          title="${s.topic ? esc(s.topic) + ' · ' : ''}${esc(t('Part {n}', {n: s.n}))} · ${esc(ST[s.pick] || s.pick)}${s.by === 'claude' ? ` (${ta("Claude's")})` : s.by === 'user' ? ` (${ta('yours')})` : ''} · ${esc(tcf(s.f0))} - ${esc(tcf(s.f1))}"><i></i><span>${s.n} · ${esc(ST[s.pick] || s.pick)}</span></div>`).join('') : ''}
      ${S.captions.map(c => `<div class="edit edcap${on('cap', sel && sel.graphic === c.graphic && sel.cue === c.cue)}${c.edited ? ' edited' : ''}${c.tail ? ' tail' : ''}" data-k="cap" data-g="${esc(c.graphic)}" data-cue="${c.cue}"${c.tail ? ' data-tail="1"' : ''}
          style="left:${(c.f * pxf).toFixed(1)}px;width:${Math.max(6, c.len * pxf).toFixed(1)}px;top:${y.cap}px;height:${ED_ROW.cap - 5}px" title="${esc(tcf(c.f))} - ${esc(tcf(c.f + c.len - 1))}${c.tail ? ' · ' + ta('the end of a caption said over the cut - drag it where it starts') : ''}"><span>${esc(c.text)}</span>${c.tail ? '' : '<i class="edh l"></i><i class="edh r"></i>'}</div>`).join('')}
      ${R.G.map(g => `<div class="edit edgi${on('gfx', sel && sel.id === g.id)}${g.new ? ' new' : ''}" data-k="gfx" data-id="${esc(g.id)}" style="left:${(g.start * pxf).toFixed(1)}px;width:${Math.max(8, (g.end - g.start + 1) * pxf).toFixed(1)}px;top:${y.gfx + R.row.get(g.id) * ED_ROW.gfx}px;height:${ED_ROW.gfx - 5}px"
          title="${esc(tcf(g.start))} - ${esc(tcf(g.end))}"><span>${esc(edGfxName(g, S, lib))}</span><i class="edh l"></i><i class="edh r"></i></div>`).join('')}
      ${S.shots.map(shotHtml).join('')}${y.shot != null ? trackExtras(y) : ''}
      ${y.fx != null ? (S.effects || []).map(x => `<div class="edit edfx${on('fx', sel && sel.id === x.id)}" data-k="fx" data-id="${esc(x.id)}" style="left:${(x.f * pxf).toFixed(1)}px;width:${Math.max(10, x.len * pxf).toFixed(1)}px;top:${y.fx + Math.min(F.n - 1, F.row.get(x.id) || 0) * ED_ROW.fx}px;height:${ED_ROW.fx - 6}px"
          title="${esc(edFxLabel(x.label))} · ${esc(tcf(x.f))} - ${esc(tcf(x.f + x.len - 1))}"><span>${esc(edFxLabel(x.label))}</span>${x.can.includes('len') ? '<i class="edh r"></i>' : ''}</div>`).join('') : ''}
      ${S.sfx.map((q, i) => `<div class="edit edsfx${on('sfx', sel && sel.key === sfxOf(q))}" data-k="sfx" data-i="${i}" style="left:${(q.f * pxf).toFixed(1)}px;width:${Math.max(18, (q.len_s || 0.3) * S.fps * pxf).toFixed(1)}px;top:${y.sfx + Math.min(Q.n - 1, Q.row[i]) * ED_ROW.sfx}px;height:${ED_ROW.sfx - 6}px;--h:${meHue(q.kind)}"
          title="${esc(edKind(q.kind))} · ${esc(tcf(q.f))}${q.what ? ' · ' + esc(q.what) : ''}"><b>${esc(edKind(q.kind))}</b></div>`).join('')}
      <canvas class="edwave${S.sound === 'song' ? ' song' : ''}${sel && sel.k === 'song' ? ' on' : ''}" width="${Math.min(16000, W)}" height="${ED_ROW.wave - 8}" style="top:${y.wave + 2}px;width:${W}px"${S.sound === 'song' ? ` title="${ta('The song - drag it to start the video at another moment of it; click for its volume')}"` : ''}></canvas>
      <div class="edins" hidden></div><div class="edph" style="height:${H}px"><i></i></div><div class="edtip" hidden></div>`;
    $('#edheads', el).style.height = `${H}px`;
    $('#edheads', el).innerHTML = `<div style="height:${ED_ROW.ruler}px"></div>
      ${y.seg != null ? `<div class="edhd seg" style="top:${y.seg}px;height:${ED_ROW.seg}px" title="${ta('The parts this edit was built from - click one to change its edit')}">${t('Parts')}</div>` : ''}
      ${y.cap != null ? `<div class="edhd cap" style="top:${y.cap}px;height:${ED_ROW.cap}px">${t('Captions')}</div>` : ''}
      <div class="edhd gfx" style="top:${y.gfx}px;height:${R.n * ED_ROW.gfx}px">${t('Graphics')}</div>
      ${S.shots.length ? `<div class="edhd shot" style="top:${y.shot}px;height:${ED_ROW.shot}px">${S.shots[0].scene ? t('Scenes') : t('Video')}</div>` : ''}
      ${y.fx != null ? `<div class="edhd fx" style="top:${y.fx}px;height:${F.n * ED_ROW.fx}px">${t('Effects')}</div>` : ''}
      <div class="edhd sfx" style="top:${y.sfx}px;height:${Q.n * ED_ROW.sfx}px">${t('Sounds')}</div>
      <div class="edhd wave" style="top:${y.wave}px;height:${ED_ROW.wave}px">${S.sound === 'song' ? t('Song') : S.sound === 'follows' ? t('Voice') : t('Sound')}</div>`;
    paintWave(); paintHead();
    if (pv && edPvH() == null) pv.fit(true);                  // (the preview as high as the timeline leaves)
  }
  const waves = {};
  async function paintWave() {
    const cv = $('.edwave', el);
    if (!cv) return;
    const S = cur, M = base.media || {}, need = S.sound === 'song' ? ['_song'] : S.sound === 'follows' ? [...new Set(S.shots.map(s => s.src))] : [];
    for (const k of need) {
      const w = (M[k] || {}).wave;
      if (w && !waves[k]) waves[k] = await fetch(fileUrl(w)).then(r => r.json()).catch(() => ({peaks: []}));
    }
    if (cv !== $('.edwave', el)) return;
    const g = cv.getContext('2d'), Wc = cv.width, Hc = cv.height, k = Wc / (S.frames * pxf || 1);
    g.clearRect(0, 0, Wc, Hc); g.fillStyle = 'rgba(62,207,142,.55)';
    const bar = (f, v) => { const x = f * pxf * k, h = Math.max(1, v / 100 * (Hc - 2)); g.fillRect(x, (Hc - h) / 2, Math.max(1, pxf * k), h); };
    const every = Math.max(1, Math.floor(1 / Math.max(pxf * k, 1e-6)));
    if (S.sound === 'song') {                                // (a mastered song is loud all through: drawn on its own
      const w = waves._song || {}, p = w.peaks || [], o = Math.round((S.song_cut || {}).start_s * S.fps || 0);   // range,
      if (w.lo == null && p.length) { const q = [...p].sort((a, b) => a - b); w.lo = q[Math.floor(q.length * 0.05)]; w.hi = q[q.length - 1]; }   // its quiet
      const span = Math.max(1, (w.hi || 100) - (w.lo || 0));                                                     // parts show)
      for (let f = 0; f < S.frames; f += every) bar(f, clamp(((p[f + o] || 0) - (w.lo || 0)) / span * 100, 2, 100)); }
    else if (S.sound === 'follows') S.shots.forEach(s => { const p = (waves[s.src] || {}).peaks || [];
      for (let f = s.start; f <= s.end; f += every) bar(f, p[edSrcAt({...s, jumps: null}, f)] || 0); });
  }
  let keyF = -1, keyT = 0;
  function keysFollow() {                                    // the keyframe rows at the playhead (a few times a second while playing)
    const kb = $('#edkeysbox', el);
    if (!kb || keyF === prevF || !sel || sel.k !== 'shot' || kb.contains(document.activeElement) || kb.querySelector('.ednl.drag')) return;
    const now = performance.now();
    if (pv && pv.playing && now - keyT < 150) return;
    const s = cur.shots.find(x => x.id === sel.id);
    if (!s) return;
    keyF = prevF; keyT = now; kb.innerHTML = keyRows(s); bindKeys(kb, s);
  }
  function paintHead() {
    if (cur) { keysFollow(); capsFollow(); }
    const h = $('.edph', el);
    if (h) h.style.left = `${prevF * pxf}px`;
    const tm = $('#edtime', el);
    if (tm && cur) tm.innerHTML = `f${prevF} <span class="tc">${tc(prevF, cur.fps)}</span> <span class="muted">/ ${tc(Math.max(0, cur.frames - 1), cur.fps)}</span>`;
    const sp = $('#edsplit', el), s = cur && shotAt(prevF);
    if (sp) sp.disabled = !s || s.start === prevF || cur.timing_locked || saving;
    const ca = $('#edcapadd', el);
    if (ca && cur) { ca.hidden = !capPieces().length; ca.disabled = !capPieceAt(prevF) || !!capAt(prevF) || saving; }
    if (cur && (addTab === 'fx' || addTab === 'tr') && ctxKey() !== lastCtx) drawAdd();    // (another shot / cut: its reasons)
    const at = $('#edadd .edat .mono', el);
    if (at && cur) at.textContent = tcf(prevF);
    const cs = $('#edcsplit', el), sc0 = sel && sel.k === 'cap' && cur && cur.captions.find(x => x.graphic === sel.graphic && x.cue === sel.cue);
    if (cs) cs.disabled = !sc0 || prevF <= sc0.f || prevF > sc0.f + sc0.len - 1 || saving;
    // keep the playhead in view while playing
    const sc = $('#edscroll', el);
    if (pv && pv.playing && sc) { const x = prevF * pxf; if (x < sc.scrollLeft || x > sc.scrollLeft + sc.clientWidth - 40) sc.scrollLeft = Math.max(0, x - 60); }
  }
  // ---------------------------------------------------------------- dragging on the timeline
  const canvas = () => $('#edcanvas', el);
  const fAt = e => { const r = canvas().getBoundingClientRect(); return clamp(Math.floor((e.clientX - r.left) / pxf), 0, cur.frames - 1); };
  function snapPts(skip) {
    const S = cur, pts = [0, S.frames, prevF];
    S.shots.forEach(s => { if (s.id !== skip) pts.push(s.start, s.end + 1); });
    S.graphics.forEach(g => { if (g.id !== skip && !g.captions) pts.push(g.start, g.end + 1); });
    S.sfx.forEach(q => pts.push(q.f));
    return pts;
  }
  function snapD(d, edges, skip) {                            // d frames, the item's edges at +d snapped to the nearest point
    if (!snap) return d;
    let best = null;
    for (const p of snapPts(skip)) for (const e of edges) { const dd = p - e; if (Math.abs(dd - d) * pxf <= ED_SNAP_PX && (best === null || Math.abs(dd - d) < Math.abs(best - d))) best = dd; }
    return best === null ? d : best;
  }
  const tip = (e, html) => { const tp = $('.edtip', el), r = canvas().getBoundingClientRect(); tp.hidden = !html; tp.innerHTML = html || ''; tp.style.left = `${e.clientX - r.left + 12}px`; tp.style.top = `${e.clientY - r.top - 30}px`; };
  const dLabel = d => `${d > 0 ? '+' : ''}${d} f · ${d > 0 ? '+' : d < 0 ? '−' : ''}${dec(Math.abs(d) / fps())} s`;
  let drag = null;
  function onDown(e) {
    if (e.button || !cur || saving) return;
    if (e.target.closest('.edcutb')) return;                // (the + on a cut: its click adds a transition)
    const it = e.target.closest('.edit');
    if (!it && e.target.classList.contains('song') && cur.song) {   // the song: a click selects it, a drag slides it
      drag = {k: 'song', it: e.target, x0: e.clientX, moved: false, d: 0, s0: cur.song_cut.start_s};
      canvas().setPointerCapture(e.pointerId); return;
    }
    if (!it) {                                               // the ruler / an empty place: the playhead goes there
      if (!pv) return;
      drag = {k: 'scrub'}; canvas().setPointerCapture(e.pointerId); pv.seek(fAt(e));
      if (sel && !e.target.closest('.edruler')) { sel = null; drawTop(); drawInsp(); $$('.edit.on', el).forEach(x => x.classList.remove('on')); }
      return;
    }
    const k = it.dataset.k, r = it.getBoundingClientRect(), x = e.clientX - r.left;
    const fxc = k === 'fx' ? (cur.effects || []).find(q => q.id === it.dataset.id) : null;
    const edge = (k === 'shot' && !cur.timing_locked) || k === 'gfx' || k === 'tr' || (k === 'cap' && !it.dataset.tail) ? (x < 8 ? 'start' : x > r.width - 8 ? 'end' : '')
      : fxc && fxc.can.includes('len') && x > r.width - 8 ? 'end' : '';
    drag = {k, it, edge, x0: e.clientX, moved: false, d: 0, fx: fxc, tail: !!it.dataset.tail, slip: k === 'shot' && !edge && e.altKey && !cur.timing_locked, fd: fAt(e)};
    if (k === 'shot') drag.s = cur.shots.find(s => s.id === it.dataset.id);
    if (k === 'gfx') drag.g = cur.graphics.find(g => g.id === it.dataset.id);
    if (k === 'sfx') drag.q = cur.sfx[+it.dataset.i];
    if (k === 'cap') drag.c = cur.captions.find(c => c.graphic === it.dataset.g && c.cue === +it.dataset.cue);
    if (k === 'tr') drag.tr = (cur.transitions || []).find(x => x.shot === it.dataset.id);
    if (k === 'key') { drag.kf = +it.dataset.f; drag.ks = it.dataset.s; }
    if (k === 'seg') drag.sg = +it.dataset.n;               // (a part: a click only - it moves with its cuts)
    canvas().setPointerCapture(e.pointerId);
  }
  function onMove(e) {
    if (!drag) { const it = e.target.closest && e.target.closest('.edit'); canvas().style.cursor = '';
      if (it && (it.dataset.k === 'gfx' || it.dataset.k === 'tr' || (it.dataset.k === 'cap' && !it.dataset.tail) || (it.dataset.k === 'shot' && !cur.timing_locked))) { const r = it.getBoundingClientRect(), x = e.clientX - r.left; if (x < 8 || x > r.width - 8) canvas().style.cursor = 'ew-resize'; }
      else if (it && it.dataset.k === 'fx' && $('.edh.r', it)) { const r = it.getBoundingClientRect(); if (e.clientX > r.right - 8) canvas().style.cursor = 'ew-resize'; }
      return; }
    if (drag.k === 'scrub') { if (pv) pv.seek(fAt(e)); return; }
    if (drag.tail || drag.k === 'seg') return;               // (a caption's end on the next shot, a part: a click only)
    const dx = e.clientX - drag.x0;
    if (!drag.moved && Math.abs(dx) < 4) return;
    if (drag.k === 'song') {                                 // dragged left = later in the song (CapCut's audio track)
      drag.moved = true;
      const s = clamp(drag.s0 - dx / pxf / cur.fps, 0, Math.max(0, songMax()));
      drag.s = s; drag.it.style.transform = `translateX(${((drag.s0 - s) * cur.fps * pxf).toFixed(1)}px)`;
      tip(e, t('The video starts at {at} of the song', {at: songTime(s)})); return;
    }
    if (drag.k === 'fx' && !drag.edge && !drag.fx.can.includes('move')) return;    // (a click selects it)
    if (drag.k === 'tr' && !drag.edge) return;
    drag.moved = true;
    let d = Math.round(dx / pxf);
    const it = drag.it, N = cur.frames;
    if (drag.k === 'shot' && drag.edge) {
      const s = drag.s, len = s.end - s.start + 1;
      if (drag.edge === 'end') { d = clamp(snapD(d, [s.end + 1], s.id), -(len - 1), s.room_end); it.style.width = `${(len + d) * pxf}px`;
        tip(e, `${dLabel(d)}<br><span class="muted">${d < 0 ? t('shorter') : d > 0 ? t('more of its clip') : ''}</span>`); }
      else { d = clamp(snapD(d, [s.start], s.id), -s.room_start, len - 1); it.style.left = `${(s.start + d) * pxf}px`; it.style.width = `${(len - d) * pxf}px`;
        tip(e, `${dLabel(-d)}<br><span class="muted">${d > 0 ? t('shorter') : d < 0 ? t('more of its clip') : ''}</span>`); }
    } else if (drag.k === 'shot' && drag.slip) {              // Alt: slip - the frames stay, the clip moves under them
      const s = drag.s;
      d = s.special ? 0 : clamp(-d, -s.room_start, s.room_end); slipShow(s, d); tip(e, slipWords(d));
    } else if (drag.k === 'shot') {                           // reorder: where it would go
      it.classList.add('dragging'); it.style.transform = `translateX(${dx}px)`;
      const fp = fAt(e), others = cur.shots.filter(s => s.id !== drag.s.id);
      const k = others.filter(s => (s.start + s.end) / 2 < fp).length, ins = $('.edins', el);
      drag.to = k;
      const xIns = k < others.length ? others[k].start : others.length ? others[others.length - 1].end + 1 : 0;
      ins.hidden = false; ins.style.left = `${xIns * pxf - 2}px`; ins.style.top = `${lanes().y.shot - 4}px`; ins.style.height = `${ED_ROW.shot + 2}px`;
      tip(e, t('Put it at place {k}', {k: k + 1}));
    } else if (drag.k === 'gfx') {
      const g = drag.g, len = g.end - g.start + 1;
      if (drag.edge === 'start') { d = clamp(snapD(d, [g.start], g.id), -g.start, len - 1); it.style.left = `${(g.start + d) * pxf}px`; it.style.width = `${(len - d) * pxf}px`; tip(e, `${t('Starts')} ${tcf(g.start + d)}`); }
      else if (drag.edge === 'end') { d = clamp(snapD(d, [g.end + 1], g.id), -(len - 1), N - 1 - g.end); it.style.width = `${(len + d) * pxf}px`; tip(e, `${t('Ends')} ${tcf(g.end + d)}`); }
      else { d = clamp(snapD(d, [g.start, g.end + 1], g.id), -g.start, N - 1 - g.end); it.style.left = `${(g.start + d) * pxf}px`; tip(e, `${tcf(g.start + d)} · ${dLabel(d)}`); }
    } else if (drag.k === 'sfx') {
      const q = drag.q;
      d = clamp(snapD(d, [q.f], ''), -q.f, N - 1 - q.f); it.style.left = `${(q.f + d) * pxf}px`; tip(e, `${tcf(q.f + d)} · ${dLabel(d)}`);
    } else if (drag.k === 'fx') {
      const x = drag.fx, last = x.f + x.len - 1;
      if (drag.edge === 'end') { d = clamp(snapD(d, [last + 1], ''), 2 - x.len, N - 1 - last); it.style.width = `${(x.len + d) * pxf}px`; tip(e, `${tn(x.len + d, '{n} frame', '{n} frames')} · ${dec((x.len + d) / cur.fps)} s`); }
      else { d = clamp(snapD(d, [x.f, last + 1], ''), -x.f, N - 1 - last); it.style.left = `${(x.f + d) * pxf}px`; tip(e, `${tcf(x.f + d)} · ${dLabel(d)}`); }
    } else if (drag.k === 'tr') {                            // its length, the same on both sides of the cut
      const x = drag.tr, n = clamp(x.len + 2 * (drag.edge === 'end' ? d : -d), 2, x.max), f0 = Math.round(x.f + (x.len - n) / 2);
      it.style.left = `${f0 * pxf}px`; it.style.width = `${Math.max(16, n * pxf)}px`; d = n;
      tip(e, `${tn(n, '{n} frame', '{n} frames')} · ${dec(n / cur.fps)} s`);
    } else if (drag.k === 'key') {                           // a diamond: every key on its frame, inside its shot
      const s = cur.shots.find(x => x.id === drag.ks), f = drag.kf;
      d = clamp(snapD(d, [f], ''), s.start - f, s.end - f); it.style.left = `${(f + d) * pxf}px`; tip(e, `${tcf(f + d)} · ${dLabel(d)}`);
    } else if (drag.k === 'cap') {                           // inside its shot, never over the captions beside it
      const c = drag.c, len = c.len, mn = Math.min(len, c.min || 1), last = c.f + len - 1;
      const lim = (raw, lo, hi) => { d = clamp(raw, lo, hi); return d !== raw ? `<br><span class="muted">${t('as far as it goes: the edge of its shot, or the caption beside it')}</span>` : ''; };
      if (drag.edge === 'start') { const why = lim(snapD(d, [c.f], ''), c.lo - c.f, len - mn); it.style.left = `${(c.f + d) * pxf}px`; it.style.width = `${(len - d) * pxf}px`; tip(e, `${t('Starts')} ${tcf(c.f + d)}${why}`); }
      else if (drag.edge === 'end') { const why = lim(snapD(d, [last + 1], ''), mn - len, c.hi - last); it.style.width = `${(len + d) * pxf}px`; tip(e, `${t('Ends')} ${tcf(last + d)}${why}`); }
      else { const why = lim(snapD(d, [c.f, last + 1], ''), c.lo - c.f, c.hi - last); it.style.left = `${(c.f + d) * pxf}px`; tip(e, `${tcf(c.f + d)} · ${dLabel(d)}${why}`); }
    }
    drag.d = d;
  }
  function onUp() {
    const D = drag;
    drag = null;
    if (!D) return;
    const tp = $('.edtip', el), ins = $('.edins', el);
    if (tp) tp.hidden = true;
    if (ins) ins.hidden = true;
    if (D.k === 'scrub') return;
    if (D.k === 'song') {
      if (!D.moved) { sel = {k: 'song'}; draw(); return; }
      D.it.style.transform = '';
      if (Math.abs(D.s - D.s0) < 0.05) return drawTL();
      return setSong(D.s, null);
    }
    if (!D.moved) {                                          // a click: it is selected
      sel = D.k === 'shot' ? {k: 'shot', id: D.s.id} : D.k === 'gfx' ? {k: 'gfx', id: D.g.id} : D.k === 'sfx' ? {k: 'sfx', key: sfxOf(D.q)}
        : D.k === 'fx' ? {k: 'fx', id: D.fx.id} : D.k === 'tr' ? {k: 'tr', id: D.tr.shot} : D.k === 'key' ? {k: 'key', id: D.ks, f: D.kf}
        : D.k === 'seg' ? {k: 'seg', id: D.sg} : {k: 'cap', graphic: D.c.graphic, cue: D.c.cue};
      if (D.k === 'key' && pv) pv.seek(D.kf);
      else if (D.k === 'shot' && pv && (prevF < D.s.start || prevF > D.s.end)) pv.seek(D.fd);   // (its keys need the playhead on it)
      if (D.k === 'cap') capFocus = 'show';                  // (its row in the captions list: in sight, marked)
      draw(); return;
    }
    const d = D.d;
    if (D.k === 'shot' && D.edge) {
      const s = D.s, v = {shot: s.n};
      if (!d) return drawTL();
      if (D.edge === 'end') push({op: 'trim', shot: s.id, side: 'end', by: d}, d < 0 ? tn(-d, 'Shot {shot}: {n} frame off its end', 'Shot {shot}: {n} frames off its end', v) : tn(d, 'Shot {shot}: {n} frame more at its end', 'Shot {shot}: {n} frames more at its end', v));
      else push({op: 'trim', shot: s.id, side: 'start', by: -d}, d > 0 ? tn(d, 'Shot {shot}: {n} frame off its start', 'Shot {shot}: {n} frames off its start', v) : tn(-d, 'Shot {shot}: {n} frame more at its start', 'Shot {shot}: {n} frames more at its start', v));
      sel = {k: 'shot', id: s.id};
    } else if (D.k === 'shot' && D.slip) {
      if (!d) { slipShow(D.s, 0); return drawTL(); }
      slipIt(D.s, d);
    } else if (D.k === 'shot') {
      const i = cur.shots.findIndex(s => s.id === D.s.id);
      if (D.to == null || D.to === i) return drawTL();
      push({op: 'move', shot: D.s.id, to: D.to}, t('Shot {n} moved to place {k}', {n: D.s.n, k: D.to + 1}));
      sel = {k: 'shot', id: D.s.id};
    } else if (D.k === 'gfx') {
      const g = D.g, nm = edGfxName(g, cur, lib);
      if (!d) return drawTL();
      if (D.edge) push({op: 'gtrim', layer: g.id, side: D.edge, by: d}, D.edge === 'start' ? t('{graphic}: starts at {at}', {graphic: nm, at: tcf(g.start + d)}) : t('{graphic}: ends at {at}', {graphic: nm, at: tcf(g.end + d)}));
      else push({op: 'gmove', layer: g.id, by: d}, t('{graphic}: moved to {at}', {graphic: nm, at: tcf(g.start + d)}));
      sel = {k: 'gfx', id: g.id};
    } else if (D.k === 'sfx') {
      const q = D.q;
      if (!d) return drawTL();
      push({op: 'sfx', f: q.f, kind: q.kind, to: q.f + d}, t('{sound} at {from}: moved to {to}', {sound: edKind(q.kind), from: tcf(q.f), to: tcf(q.f + d)}));
      sel = {k: 'sfx', key: `${q.f + d}|${q.kind}`};
    } else if (D.k === 'fx') {
      const x = D.fx, nm = edFxLabel(x.label);
      if (!d) return drawTL();
      if (D.edge) { push({op: 'fxset', id: x.id, len: x.len + d}, t('{effect} at {at}: {n} frames long', {effect: nm, at: tcf(x.f), n: x.len + d})); sel = {k: 'fx', id: x.id}; }
      else { push({op: 'fxmove', id: x.id, by: d}, t('{effect}: moved to {at}', {effect: nm, at: tcf(x.f + d)})); sel = {k: 'fx', id: x.id.replace(/:\d+$/, ':' + (x.f + d))}; }
    } else if (D.k === 'tr') {
      const x = D.tr;
      if (d === x.len) return drawTL();
      push({op: 'trans', shot: x.shot, len: d}, t('{transition} at {at}: {n} frames long', {transition: edTrLabel(x.label), at: tcf(x.cut), n: d}));
      sel = {k: 'tr', id: x.shot};
    } else if (D.k === 'key') {
      if (!d) return drawTL();
      push({op: 'kmove', shot: D.ks, f: D.kf, to: D.kf + d}, t('Keyframe at {from}: moved to {to}', {from: tcf(D.kf), to: tcf(D.kf + d)}));
      sel = {k: 'key', id: D.ks, f: D.kf + d};
    } else if (D.k === 'cap') {
      const c = D.c;
      if (!d) return drawTL();
      if (D.edge) push({op: 'captrim', graphic: c.graphic, cue: c.cue, side: D.edge, to: D.edge === 'start' ? c.f + d : c.f + c.len - 1 + d}, D.edge === 'start'
        ? t('Caption at {at}: starts at {to}', {at: tcf(c.f), to: tcf(c.f + d)}) : t('Caption at {at}: ends at {to}', {at: tcf(c.f), to: tcf(c.f + c.len - 1 + d)}));
      else push({op: 'capmove', graphic: c.graphic, cue: c.cue, by: d}, t('Caption at {from}: moved to {to}', {from: tcf(c.f), to: tcf(c.f + d)}));
      sel = {k: 'cap', graphic: c.graphic, cue: c.cue};
    }
  }
  // ---------------------------------------------------------------- the panel on the right: what is selected
  const sound = q => q.sound ? (base.library.recorded.find(x => x.file === q.sound) || {name: q.sound}).name : t('made-up');
  function brandSwatches() {
    const b = BRAND_DATA, cols = b ? brandPalette(b, 6) : [];
    return cols.length ? `<span class="edsw">${cols.map(c => `<button type="button" class="edswc" data-col="${esc(c)}" style="background:${esc(c)}" title="${ta('Your brand: {colour}', {colour: c})}"></button>`).join('')}</span>` : '';
  }
  function setRows(g, list) {
    return list.map(s => { const v = g.values[s.id], s2 = {...s, value: v}, lab = t(s.label || s.id || '');
      if (s.type === 'number' && s.min != null && s.max != null && Number.isFinite(+v))
        return edNum({id: 'set:' + s.id, label: lab, value: +v, min: +s.min, max: +s.max, step: +s.step || 1, dflt: s.default != null ? +s.default : null, tip: lab});
      const changed = s.default != null && String(v) !== String(s.default);
      return `<label class="edset" title="${esc(lab)}"><span>${esc(lab)}</span><span class="edin">${gsetInput(s2)}${s.type === 'color' ? brandSwatches() : ''}</span>
        <button type="button" class="ednreset" data-reset="${esc(s.id)}"${changed ? '' : ' hidden'} title="${ta('Back to how it was')}">↺</button></label>`; }).join('');
  }
  function bindSets(box, g) {
    const nm = edGfxName(g, cur, lib);
    const commit = i => { const key = i.dataset.set, v = gsetValue(i);
      if (String(v) === String(g.values[key])) return;
      push({op: 'set', graphic: g.id, key, value: v}, t('{graphic}: {setting} changed', {graphic: nm, setting: t(((cur.folders[g.dir] || {}).settings || []).find(s => s.id === key)?.label || key)})); };
    $$('[data-set]', box).forEach(i => {
      if (i.type === 'text' || i.tagName === 'TEXTAREA') { i.onchange = () => commit(i); i.onkeydown = e => { if (e.key === 'Enter') { e.preventDefault(); i.blur(); } }; }
      else i.onchange = () => commit(i);
    });
    $$('[data-col]', box).forEach(b => b.onclick = () => { const i = $('input[type=color]', b.closest('.edin')); if (i) { i.value = b.dataset.col.toLowerCase(); commit(i); } });
    const decl = (cur.folders[g.dir] || {}).settings || [], lab = key => t(decl.find(s => s.id === key)?.label || key);
    $$('[data-reset]', box).forEach(b => b.onclick = e => { e.preventDefault(); const sd = decl.find(s => s.id === b.dataset.reset);
      if (sd && sd.default != null) push({op: 'set', graphic: g.id, key: sd.id, value: sd.default}, t('{graphic}: {setting} back to how it was', {graphic: nm, setting: lab(sd.id)})); });
    $$('[data-num^="set:"]', box).forEach(r => { const key = r.dataset.num.slice(4), sd = decl.find(s => s.id === key);
      if (!sd) return;
      edNumBind(box, {id: r.dataset.num, min: +sd.min, max: +sd.max, step: +sd.step || 1, dflt: sd.default != null ? +sd.default : null,
        commit: v => push({op: 'set', graphic: g.id, key, value: v}, t('{graphic}: {setting} {v}', {graphic: nm, setting: lab(key), v: numLoc(v)}))}); });
  }
  // the panel is drawn again after every change: it keeps where it was scrolled (the same item), the field in use (its
  // caret too) and the sections as they were left (the user, 2026-10-27: "a real pain ... to use realistically" - a
  // change closed More settings and jumped back to the top)
  const selKey = () => (!sel ? '' : sel.k === 'cap' ? 'cap' : `${sel.k}:${sel.id || sel.key || ''}`);
  const fidOf = a => (a.dataset.fid ? `[data-fid="${CSS.escape(a.dataset.fid)}"]` : a.dataset.set ? `[data-set="${CSS.escape(a.dataset.set)}"]` : a.id ? `#${CSS.escape(a.id)}` : null);
  function drawInsp() {
    const box = $('#edinsp', el);
    if (!box) return;
    const top = box.scrollTop, a = document.activeElement, fid = a && box.contains(a) ? fidOf(a) : null, was = box.dataset.item;
    const caret = fid && /^(text|search|)$/.test(a.type || '') && typeof a.selectionStart === 'number' ? [a.selectionStart, a.selectionEnd] : null;
    inspFocused = false;
    drawInsp0();
    box.dataset.item = selKey();
    const secs = edSecs();
    $$('details[data-sec]', box).forEach(d => { if (d.dataset.sec in secs) d.open = secs[d.dataset.sec]; d.ontoggle = () => edSecSet(d.dataset.sec, d.open); });
    if (box.dataset.item === was && !inspFocused) box.scrollTop = top;
    const n = !inspFocused && fid && $(fid, box);
    if (n && !n.disabled) { n.focus({preventScroll: true}); if (caret) try { n.setSelectionRange(...caret); } catch (e) { /* not a text field */ } }
  }
  // 2026-11-03 (docs\plans.md 0.6.1 step 1: "the Editor shows the line under each clip and the user can correct it (a
  // correction wins)"): what the shot shows = the clip catalogue's line of the moment it uses (Claude's or yours) -
  // corrected here (POST .../catalogue/line = the user's line; Claude's never replace it). No catalogue = no section.
  function lineSec(S, s) {
    const L = (S.lines || {})[s.id];
    if (!L) return '';
    const y = L.say || {};
    if (lineEdit === s.id) return `<details class="edsec" data-sec="shot.line" open><summary>${t('What it shows')}</summary>
      <textarea id="edlnw" rows="2" maxlength="200" placeholder="${ta('a man walks to camera on a wet street at night')}">${esc(y.what || '')}</textarea>
      <div class="edchips">${ED_SIZES().map(([k, l]) => `<button data-lsize="${k}" class="${y.size === k ? 'on' : ''}">${l}</button>`).join('')}</div>
      <input id="edlnwh" maxlength="80" placeholder="${ta('Where: a city street')}" value="${esc(y.where || '')}">
      <input id="edlnt" maxlength="200" placeholder="${ta('Tags: person, street, night')}" value="${esc((y.tags || []).join(', '))}">
      <div class="row edbtns"><button class="btn sm pri" id="edlnok">${t('Save')}</button><button class="btn sm ghost" id="edlnno">${t('Cancel')}</button></div></details>`;
    const more = [y.size && (ED_SIZES().find(([k]) => k === y.size) || [0, y.size])[1], y.where && esc(y.where), ...(y.tags || []).map(esc)].filter(Boolean);
    return `<details class="edsec" data-sec="shot.line" open><summary>${t('What it shows')}</summary>
      <div class="edline">${y.what ? esc(y.what) : `<span class="muted">${t('No line yet')}</span>`}${y.by === 'user' ? ` <span class="edlnby">${t('yours')}</span>` : y.by === 'claude' ? ' <span class="clchip">Claude</span>' : ''}</div>
      ${more.length ? `<div class="small muted">${more.join(' · ')}</div>` : ''}
      <button class="btn sm ghost" id="edlned"><svg class="i"><use href="#i-pen"/></svg>${y.what ? t('Correct it') : t('Write it')}</button></details>`;
  }
  function bindLine(box, S, s) {
    const L = (S.lines || {})[s.id];
    if (!L) return;
    const ed = $('#edlned', box); if (ed) ed.onclick = () => { lineEdit = s.id; drawInsp(); const w = $('#edlnw', box); if (w) w.focus(); };
    const no = $('#edlnno', box); if (no) no.onclick = () => { lineEdit = null; drawInsp(); };
    let size = (L.say || {}).size || '';
    $$('[data-lsize]', box).forEach(b => b.onclick = () => { size = size === b.dataset.lsize ? '' : b.dataset.lsize;
      $$('[data-lsize]', box).forEach(x => x.classList.toggle('on', x.dataset.lsize === size)); });
    const ok = $('#edlnok', box);
    if (ok) ok.onclick = async () => {
      try { const r = await api(`/api/project/${encodeURIComponent(P.name)}/catalogue/line`,
                                {moment: L.m, what: $('#edlnw', box).value, size, where: $('#edlnwh', box).value, tags: $('#edlnt', box).value});
        [cur, base].forEach(X => Object.values((X && X.lines) || {}).forEach(x => { if (x.m === L.m) x.say = r.say; }));   // (every shot of it)
        lineEdit = null; toast(t('Saved - Claude keeps your line'), 'ok'); draw(); }
      catch (e) { toast(e.message, 'err'); }
    };
  }
  function drawInsp0() {
    const box = $('#edinsp', el), S = cur;
    if (!S) return;
    if (saving) { box.innerHTML = `<div class="edempty">${neIcon('i-restart', '--ed1')}<b>${t('Saving your changes')}</b><span class="small muted">${t('The new version shows here when it is ready - change it after that.')}</span></div>`; return; }
    if (!sel) {
      box.innerHTML = `<div class="edempty">${neIcon('i-edit', '--ed1')}<b>${t('Click something on the timeline')}</b>
        <span class="small muted">${t('A clip, a graphic, a caption or a sound: its settings show here.')}</span>
        <ul class="edkeys small"><li>${t('<b>Drag</b> a clip to move it, its <b>edges</b> to trim it')}</li><li>${t('<b>Drag</b> a graphic or a sound to another moment')}</li>
          <li>${t('<b>S</b> splits at the playhead · <b>Delete</b> removes')}</li><li>${t('<b>Space</b> plays · <b>Ctrl+Z</b> undoes')}</li>
          <li>${t('Add sounds and templates from the panel on the left - drag them onto the timeline')}</li></ul>
        ${S.timing_locked ? `<div class="small bad">${t('This video\'s sound was made in a way the Editor cannot cut again, so its shots keep their timing - ask Claude for those changes.')}</div>` : ''}</div>`;
      return;
    }
    if (sel.k === 'seg') return segInsp(box);
    if (sel.k === 'shot') {
      const s = S.shots.find(x => x.id === sel.id);
      if (!s) { sel = null; return drawInsp(); }
      const lock = S.timing_locked, under = shotAt(prevF) === s && prevF > s.start, muted = s.db <= S.vol[0];
      if (s.scene) return sceneInsp(box, s, under);
      const sp = S.speeds || [0.25, 4];
      // (2026-10-27: sections that stay as the user left them instead of tabs - everything of a shot on one panel, as
      // Premiere's Properties panel shows a clip)
      box.innerHTML = `<div class="edih"><span class="eddot shot"></span><b>${t('Shot {n}', {n: s.n})}</b><span class="small muted">${dec((s.end - s.start + 1) / S.fps)} s</span></div>
        <div class="small muted">${frange(s.start, s.end, S.fps)}</div>
        ${lineSec(S, s)}
        ${edFrameSec(s)}
        <details class="edsec" data-sec="shot.look" open><summary>${t('Position and size')}</summary><div id="edkeysbox">${keyRows(s)}</div>${edBlendRow((drawOf(s.id) || {}).blend)}</details>
        <details class="edsec" data-sec="shot.speed" open><summary>${t('Speed')}</summary>
          ${edNum({id: 'speed', label: t('Speed'), value: s.speed, min: sp[0], max: sp[1], step: 0.05, unit: '×', dflt: 1, disabled: lock || s.special})}
          <div class="edchips">${ED_SPEEDS.map(x => `<button class="${Math.abs(x - s.speed) < 1e-6 ? 'on' : ''}" data-speed="${x}"${lock || s.special ? ' disabled' : ''}>${numLoc(x)}×</button>`).join('')}</div>
          <div class="small muted">${t('Slower = longer, faster = shorter; its sound keeps its pitch.')}</div></details>
        ${S.sound === 'follows' ? `<details class="edsec" data-sec="shot.sound" open><summary>${t('Sound')}</summary>
          ${edNum({id: 'vol', label: t('Volume'), value: muted ? -30 : Math.round(s.db), min: -30, max: S.vol[1], step: 1, unit: 'dB', dflt: 0, disabled: muted || lock,
            after: `<button class="btn sm ghost${muted ? ' on' : ''}" id="edmute" aria-pressed="${muted}"${lock ? ' disabled' : ''} title="${muted ? ta('Its sound back on') : ta('Mute')}">${muted ? '🔇' : '🔊'}</button>`})}</details>` : ''}
        <details class="edsec" data-sec="shot.clip"><summary>${t('Clip')}</summary>
        ${S.clips.length > 1 ? `<div class="edlbl">${t('Clip')}</div>
          <select id="edtake"${lock ? ' disabled' : ''}>${S.clips.map(c => `<option value="${esc(c.id)}"${c.id === s.src ? ' selected' : ''}>${esc(c.name)}</option>`).join('')}</select>` : ''}
        <div class="edlbl">${t('Part of its clip')}</div>
        <div class="row"><input type="range" id="edslip" min="${-s.room_start}" max="${s.room_end}" step="1" value="0"${lock || s.special || !(s.room_start || s.room_end) ? ' disabled' : ''}>
          <span class="mono small" id="edslipv">${t('as it is')}</span></div>
        <div class="small muted">${t('An earlier or later moment of its clip in the same frames - or Alt + drag the shot.')}</div>
        <div class="small muted">${t('Its clip has {before} before and {after} after it - drag its edges to use them.', {before: `${dec(s.room_start / S.fps)} s`, after: `${dec(s.room_end / S.fps)} s`})}</div></details>
        <div class="row edbtns"><button class="btn sm" id="edsplit2"${!under || lock ? ' disabled' : ''} title="${ta('Move the playhead inside the shot first')}">✂ ${t('Split at the playhead')}</button>
          <button class="btn sm eddanger" id="edshotdel"${lock || S.shots.length < 2 ? ' disabled' : ''}><svg class="i"><use href="#i-trash"/></svg>${t('Delete')}</button></div>
        ${s.attached.length ? `<div class="small muted">${t('Moves with it: {what}', {what: esc(s.attached.map(f => /^captions/.test(f) ? t('the captions') : f.replace(/^(v\d+_|n\d+_)?(g|d)?\d+_/, '').replace(/_m\d+$/, '').replace(/[-_]/g, ' ')).join(', '))})}</div>` : ''}
        ${lock ? `<div class="small bad">${t('This video\'s sound was made in a way the Editor cannot cut again, so its shots keep their timing - ask Claude for those changes.')}</div>` : s.special ? `<div class="small muted">${t('A held frame or a stutter: it keeps its speed.')}</div>` : ''}`;
      bindKeys(box, s);
      bindLine(box, S, s);
      edBlendBind(box, (drawOf(s.id) || {}).blend, m => push({op: 'blend', shot: s.id, value: m}, t('Shot {n}: blend {mode}', {n: s.n, mode: edBlendName(m)})));
      $$('[data-frame]', box).forEach(b => b.onclick = () => { if (b.classList.contains('on')) return;
        push({op: 'frame', shot: s.id, layout: b.dataset.frame}, t('Shot {n}: framing {how}', {n: s.n, how: b.dataset.name})); });
      $$('[data-fmode]', box).forEach(b => b.onclick = () => { if (b.classList.contains('on')) return;
        push({op: 'frame', shot: s.id, mode: b.dataset.fmode}, b.dataset.fmode === 'hold' ? t('Shot {n}: a still crop', {n: s.n}) : t('Shot {n}: the crop follows the person', {n: s.n})); });
      const setSpeed = x => { if (Math.abs(x - s.speed) > 1e-6) push({op: 'speed', shot: s.id, speed: x}, t('Shot {n}: {x}× speed', {n: s.n, x: numLoc(x)})); };
      edNumBind(box, {id: 'speed', min: sp[0], max: sp[1], step: 0.05, dflt: 1, commit: setSpeed});
      $$('[data-speed]', box).forEach(b => b.onclick = () => setSpeed(+b.dataset.speed));
      $('#edsplit2', box).onclick = () => splitHere();
      $('#edshotdel', box).onclick = () => delSel();
      const tk = $('#edtake', box);
      if (tk) tk.onchange = () => { const c = S.clips.find(x => x.id === tk.value);
        push({op: 'take', shot: s.id, src: tk.value, in: s.src === tk.value ? s.in : 0}, t('Shot {n}: now {clip}', {n: s.n, clip: c ? c.name : tk.value})); };
      const sl = $('#edslip', box);
      if (sl) { sl.oninput = () => { $('#edslipv', box).textContent = slipWords(+sl.value); slipShow(s, +sl.value); };
        sl.onchange = () => { if (+sl.value) slipIt(s, +sl.value); else slipShow(s, 0); }; }
      if (S.sound === 'follows') {
        edNumBind(box, {id: 'vol', min: -30, max: S.vol[1], step: 1, dflt: 0,
          commit: v => push({op: 'volume', shot: s.id, db: v}, t('Shot {n}: its sound {db} dB', {n: s.n, db: `${v > 0 ? '+' : ''}${v}`}))});
        $('#edmute', box).onclick = () => push({op: 'volume', shot: s.id, db: muted ? 0 : S.vol[0]},
          muted ? t('Shot {n}: its sound back on', {n: s.n}) : t('Shot {n}: muted', {n: s.n}));
      }
      return;
    }
    if (sel.k === 'key') {
      const s = S.shots.find(x => x.id === sel.id), d = s && drawOf(s.id), fs = s && d ? keyFramesOf(s) : [];
      if (!fs.length) { sel = s ? {k: 'shot', id: s.id} : null; return drawInsp(); }
      if (!fs.includes(sel.f)) sel.f = fs.reduce((a, b) => (Math.abs(b - sel.f) < Math.abs(a - sel.f) ? b : a));    // (a drag that stopped short)
      const f = sel.f, here = ED_KEY_PROPS().filter(([p]) => (edKKeys(d, p) || []).some(k => k[0] === f));
      const k0 = (edKKeys(d, here[0][0]) || []).find(k => k[0] === f), ease = (k0 && k0[2]) || 'linear';
      box.innerHTML = `<div class="edih"><span class="eddot key"></span><b>${t('Keyframe')}</b><span class="small muted">${t('Shot {n}', {n: s.n})}</span></div>
        <div class="small muted mono">${esc(tcf(f))}</div>
        <div class="edkhere">${here.map(([p, lab, unit, k, , dflt]) => `<span class="edkchip">${esc(lab)} <b>${numLoc(+(edCurve(edKSpec(d, p), S.curves, dflt)(f) * k).toFixed(unit === 'px' ? 0 : 1))}${unit}</b></span>`).join('')}</div>
        <div class="edlbl">${t('The move after it')}</div>
        <div class="edeases">${ED_KEY_EASES().map(([e, l]) => `<button data-kease="${e}" class="edease ${ease === e ? 'on' : ''}" title="${ta(ED_EASE_TIP()[e] || l)}">${edEaseIcon(e)}<span>${esc(l)}</span></button>`).join('')}</div>
        ${ease === 'hold' ? '' : `<div class="edchart" title="${ta('Drag the two handles to shape the move')}"><svg id="edchart" viewBox="-14 -46 168 232" width="168" height="232">
          <rect x="0" y="0" width="140" height="140" class="edcbox"/><path d="M0 70 H140 M70 0 V140" class="edcgrid"/>
          <line id="edch1" class="edchl"/><line id="edch2" class="edchl"/><path id="edccv" class="edccv"/>
          <circle id="edcp1" r="7" class="edchd"/><circle id="edcp2" r="7" class="edchd"/></svg>
          <div class="small muted" id="edcname">${esc((ED_KEY_EASES().find(([e]) => e === ease) || [0, t('Your curve')])[1])}</div></div>`}
        <div class="row edbtns"><button class="btn sm eddanger" id="edkdel"><svg class="i"><use href="#i-trash"/></svg>${t('Remove')}</button>
          <button class="btn sm ghost" id="edkback">${t('The whole shot')}</button></div>
        <div class="small muted">${t('Drag the diamond on the timeline to move it.')}</div>`;
      $$('[data-kease]', box).forEach(b => b.onclick = () => { if (b.dataset.kease === ease) return;
        push({op: 'kease', shot: s.id, f, ease: b.dataset.kease}, t('Keyframe at {at}: {ease}', {at: tcf(f), ease: b.textContent})); });
      const svg = $('#edchart', box);
      if (svg) {                               // the curve's two handles (Flow / After Effects' graph): drag = live, release = kept
        const b = [...(edBezOf(ease) || ED_BEZ_LIKE[ease] || [0.33, 0, 0.67, 1])], S_ = 140;
        const drawChart = () => {
          const e = `cubic(${b.map(v => +v.toFixed(2)).join(',')})`;
          $('#edccv', svg).setAttribute('d', edEasePath(e, S_, S_));
          const p1 = [b[0] * S_, S_ - b[1] * S_], p2 = [b[2] * S_, S_ - b[3] * S_];
          Object.entries({edch1: [0, S_, ...p1], edch2: [S_, 0, ...p2]}).forEach(([id, [x1, y1, x2, y2]]) => {
            const l = $('#' + id, svg); l.setAttribute('x1', x1); l.setAttribute('y1', y1); l.setAttribute('x2', x2); l.setAttribute('y2', y2); });
          $('#edcp1', svg).setAttribute('cx', p1[0]); $('#edcp1', svg).setAttribute('cy', p1[1]);
          $('#edcp2', svg).setAttribute('cx', p2[0]); $('#edcp2', svg).setAttribute('cy', p2[1]);
        };
        drawChart();
        [['#edcp1', 0], ['#edcp2', 2]].forEach(([id, k]) => $(id, svg).addEventListener('pointerdown', ev => {
          ev.preventDefault();
          const h = ev.currentTarget, m = svg.getScreenCTM().inverse();
          h.setPointerCapture(ev.pointerId);
          let moved = false;
          const move = e2 => { moved = true; const pt = new DOMPoint(e2.clientX, e2.clientY).matrixTransform(m);
            b[k] = +clamp(pt.x / S_, 0, 1).toFixed(2); b[k + 1] = +clamp(1 - pt.y / S_, -0.5, 1.5).toFixed(2); drawChart();
            $('#edcname', box).textContent = t('Your curve'); };
          const up = () => { h.removeEventListener('pointermove', move); h.removeEventListener('pointerup', up);
            const e = `cubic(${b.join(',')})`;
            if (moved && e !== ease) push({op: 'kease', shot: s.id, f, ease: e}, t('Keyframe at {at}: {ease}', {at: tcf(f), ease: t('Your curve')})); };
          h.addEventListener('pointermove', move); h.addEventListener('pointerup', up);
        }));
      }
      $('#edkdel', box).onclick = () => delSel();
      $('#edkback', box).onclick = () => { sel = {k: 'shot', id: s.id}; draw(); };
      return;
    }
    if (sel.k === 'tr') {
      const x = (S.transitions || []).find(q => q.shot === sel.id);
      if (!x) { sel = null; return drawInsp(); }
      const s = S.shots.find(q => q.id === x.shot), how = ED_TR_HOW(), nm = edTrLabel(x.label);
      box.innerHTML = `<div class="edih"><span class="eddot tr"></span><b>${t('Transition')}</b><span class="small muted">${t('into shot {n}', {n: s ? s.n : '?'})}</span></div>
        <div class="small muted">${frange(x.f, x.f + x.len - 1, S.fps)}</div>
        <div class="edtrgrid">${(S.trans_kinds || []).map(([k, l]) => `<button data-trk="${k}" class="${k === x.kind ? 'on' : ''}" title="${esc(how[k] || '')}"><span>${ED_TR_ICON[k] || '◐'}</span>${esc(edTrLabel(l))}</button>`).join('')}</div>
        ${edNum({id: 'trlen', label: t('Length'), value: x.len, min: 2, max: Math.max(2, x.max), step: 1, unit: 'f', tip: `${dec(x.len / S.fps)} s`})}
        ${x.dir ? `<div class="edlbl">${t('Direction')}</div><div class="edchips">${ED_DIRS().map(([d, a, l]) => `<button data-trd="${d}" class="${x.dir === d ? 'on' : ''}" title="${esc(l)}">${a} ${esc(l)}</button>`).join('')}</div>` : ''}
        ${x.frozen ? `<div class="small amber">${t('{n} frames hold still: a clip has no more picture there. Make it shorter, or drag the shots\' edges for more of them.', {n: x.frozen})}</div>` : ''}
        <div class="row edbtns"><button class="btn sm" id="edtrall">${t('Apply to all cuts')}</button>
          <button class="btn sm eddanger" id="edtrdel"><svg class="i"><use href="#i-trash"/></svg>${t('Remove')}</button></div>`;
      $$('[data-trk]', box).forEach(b => b.onclick = () => { const k = b.dataset.trk; if (k === x.kind) return;
        const K = (S.trans_kinds || []).find(q => q[0] === k);
        push({op: 'trans', shot: x.shot, kind: k}, t('Transition at {at}: {transition}', {at: tcf(x.cut), transition: edTrLabel(K ? K[1] : k)})); });
      edNumBind(box, {id: 'trlen', min: 2, max: Math.max(2, x.max), step: 1,
        commit: n => push({op: 'trans', shot: x.shot, len: n}, t('{transition} at {at}: {n} frames long', {transition: nm, at: tcf(x.cut), n}))});
      $$('[data-trd]', box).forEach(b => b.onclick = () => { if (b.dataset.trd === x.dir) return;
        push({op: 'trans', shot: x.shot, dir: b.dataset.trd}, t('{transition} at {at}: {dir}', {transition: nm, at: tcf(x.cut), dir: b.title})); });
      $('#edtrall', box).onclick = () => push({op: 'transall', kind: x.kind, len: x.len, ...(x.dir ? {dir: x.dir} : {})},
        t('{transition} on all {n} cuts', {transition: nm, n: plainCuts().length}));
      $('#edtrdel', box).onclick = () => delSel();
      return;
    }
    if (sel.k === 'song') {
      if (!S.song) { sel = null; return drawInsp(); }
      const C = S.song_cut, mx = songMax();
      box.innerHTML = `<div class="edih"><span class="eddot song"></span><b>${t('Song')}</b></div>
        <div class="small muted edrn">${esc(S.song.split(/[\\/]/).pop())}</div>
        ${edNum({id: 'sgstart', label: t('The video starts at'), value: +(+C.start_s).toFixed(1), min: 0, max: +Math.max(0.1, mx).toFixed(1), step: 0.1, unit: 's', disabled: mx <= 0, changed: false, tip: songTime(C.start_s)})}
        <div class="small muted">${t('of the song - or drag the song on the timeline. The cuts stay where they are.')}</div>
        ${edNum({id: 'sgdb', label: t('Volume'), value: Math.round(C.db), min: S.song_db[0], max: S.song_db[1], step: 1, unit: 'dB', dflt: 0})}
        <div class="small muted">${t('Against the sound effects - the finished video is brought to the loudness the platforms use.')}</div>`;
      edNumBind(box, {id: 'sgstart', min: 0, max: +Math.max(0.1, mx).toFixed(1), step: 0.1, commit: v => setSong(v, null)});
      edNumBind(box, {id: 'sgdb', min: S.song_db[0], max: S.song_db[1], step: 1, dflt: 0, commit: v => setSong(null, v)});
      return;
    }
    if (sel.k === 'gfx') {
      const g = S.graphics.find(x => x.id === sel.id);
      if (!g) { sel = null; return drawInsp(); }
      const fo = S.folders[g.dir] || {}, all = fo.settings || [], words = new Set((g.words || []).map(w => w.key));
      const cols = all.filter(s => s.type === 'color'), wl = all.filter(s => words.has(s.id)), rest = all.filter(s => !words.has(s.id) && s.type !== 'color');
      const T = fo.from && lib.find(x => x.id === fo.from);
      box.innerHTML = `<div class="edih"><span class="eddot gfx"></span><b>${esc(edGfxName(g, S, lib))}</b>${g.new ? `<span class="chip">${t('new')}</span>` : ''}</div>
        <div class="small muted">${T ? `${esc(t(T.name))} · ` : ''}${frange(g.start, g.end, S.fps)}</div>
        ${wl.length ? `<div class="edlbl">${t('Words')}</div>${setRows(g, wl)}` : ''}
        ${cols.length ? `<div class="edlbl">${t('Colours')}</div>${setRows(g, cols)}` : ''}
        ${(S.clips || []).length && g.fit ? `<div class="edlbl" title="${ta('Part of the shot instead of pasted on top - it shows in the render (See it rendered)')}">${t('In the shot')}</div>
          <div class="edchips edfit">${ED_FIT().map(([k, l, tip]) => `<button data-fit="${k}" class="${g.fit[k] ? 'on' : ''}" title="${ta(tip)}">${esc(l)}</button>`).join('')}</div>` : ''}
        ${edBlendRow(g.blend)}
        ${rest.length ? `<details class="edmore"><summary>${t('More settings')}</summary>${setRows(g, rest)}</details>` : ''}
        ${fo.problem ? `<div class="small bad">${esc(fo.problem)}</div>` : ''}
        <div class="row edbtns"><button class="btn sm eddanger" id="edgdel"><svg class="i"><use href="#i-trash"/></svg>${t('Remove')}</button>
          ${g.pieces > 1 ? `<button class="btn sm ghost" id="edgdelall">${t('Remove all {n} pieces', {n: g.pieces})}</button>` : ''}</div>`;
      bindSets(box, g);
      edBlendBind(box, g.blend, m => push({op: 'blend', layer: g.id, value: m}, t('{graphic}: blend {mode}', {graphic: edGfxName(g, S, lib), mode: edBlendName(m)})));
      $$('[data-fit]', box).forEach(b => b.onclick = () => { const k = b.dataset.fit, on = !g.fit[k];
        push({op: 'gfit', layer: g.id, key: k, value: on}, on ? t('{graphic}: {what} on', {graphic: edGfxName(g, S, lib), what: b.textContent})
          : t('{graphic}: {what} off', {graphic: edGfxName(g, S, lib), what: b.textContent})); });
      $('#edgdel', box).onclick = () => delSel();
      const da = $('#edgdelall', box);
      if (da) da.onclick = () => push({op: 'gdelete', layer: g.id, all: true}, t('{graphic}: removed everywhere', {graphic: edGfxName(g, S, lib)}), () => { sel = null; });
      return;
    }
    if (sel.k === 'fx') {
      // (a drag stops at an edge: the effect may have moved less than the pointer - the nearest of its kind there)
      const pre = sel.id.replace(/:-?\d+$/, ':'), at = +sel.id.slice(pre.length);
      const x = (S.effects || []).find(q => q.id === sel.id)
        || (S.effects || []).filter(q => q.id.startsWith(pre)).sort((a, b) => Math.abs(a.f - at) - Math.abs(b.f - at))[0];
      if (!x) { sel = null; return drawInsp(); }
      sel.id = x.id;
      const rg = (x.kind === 'room' && x.label === 'Room out of focus' ? [1, 40, 1, ' px'] : ED_FX_RANGE[x.kind]) || [0.05, 1, 0.05, ''], nm = edFxLabel(x.label);
      box.innerHTML = `<div class="edih"><span class="eddot fx"></span><b>${esc(nm)}</b></div><div class="small muted">${frange(x.f, x.f + x.len - 1, S.fps)}</div>
        ${x.can.includes('strength') && x.strength != null ? edNum({id: 'fxs', label: t('Strength'), value: x.strength, min: rg[0], max: rg[1], step: rg[2], unit: rg[3].trim()}) : ''}
        ${x.can.includes('len') ? edNum({id: 'fxl', label: t('Length'), value: x.len, min: 2, max: Math.max(2, Math.min(S.frames, x.len * 4, 600)), step: 1, unit: 'f', hardMax: S.frames, tip: `${dec(x.len / S.fps)} s`}) : ''}
        ${x.can.includes('ease') ? `<div class="edlbl">${t('Ease')}</div><div class="edchips">${ED_EASES().map(([k, l]) => `<button data-ease="${k}" class="${x.ease === k ? 'on' : ''}">${l}</button>`).join('')}</div>` : ''}
        <div class="small muted" style="margin-top:8px">${x.can.includes('move') ? t('Drag it on the timeline to move it. ') : ''}${t('Its sound effect follows it by itself.')}</div>
        ${x.can.includes('remove') ? `<div class="row edbtns"><button class="btn sm eddanger" id="edfxdel"><svg class="i"><use href="#i-trash"/></svg>${t('Remove')}</button></div>` : ''}`;
      edNumBind(box, {id: 'fxs', min: rg[0], max: rg[1], step: rg[2],
        commit: v => push({op: 'fxset', id: x.id, strength: v}, t('{effect} at {at}: strength {x}', {effect: nm, at: tcf(x.f), x: numLoc(v) + rg[3]}))});
      edNumBind(box, {id: 'fxl', min: 2, max: Math.max(2, Math.min(S.frames, x.len * 4, 600)), step: 1, hardMax: S.frames,
        commit: n => push({op: 'fxset', id: x.id, len: n}, t('{effect} at {at}: {n} frames long', {effect: nm, at: tcf(x.f), n}))});
      $$('[data-ease]', box).forEach(b => b.onclick = () => { if (b.dataset.ease !== x.ease) push({op: 'fxset', id: x.id, ease: b.dataset.ease}, t('{effect} at {at}: {ease}', {effect: nm, at: tcf(x.f), ease: b.textContent})); });
      const del = $('#edfxdel', box);
      if (del) del.onclick = () => delSel();
      return;
    }
    if (sel.k === 'sfx') {
      const q = S.sfx.find(x => sfxOf(x) === sel.key);
      if (!q) { sel = null; return drawInsp(); }
      const same = base.library.recorded.filter(x => x.kind === q.kind);
      box.innerHTML = `<div class="edih"><span class="eddot" style="--h:${meHue(q.kind)}"></span><b>${esc(edKind(q.kind))}</b><span class="small muted">${ftc(q.f, S.fps)}</span></div>
        ${q.what ? `<div class="small muted">${esc(q.what)}</div>` : ''}
        <div class="row" style="margin:8px 0"><button class="btn sm" id="edhear">▶ ${t('Listen')}</button><span class="small">${esc(sound(q))}</span></div>
        ${edNum({id: 'sfxdb', label: t('Volume'), value: Math.round(q.db || 0), min: -12, max: 12, step: 1, unit: 'dB', dflt: 0})}
        <div class="edlbl">${t('Its sound')}</div>
        <div class="edsounds">${[{file: 'made-up', name: t('made-up'), kind: q.kind}, ...same].map(x => `<div class="edsrow${(x.file === 'made-up' ? !q.sound : x.file === q.sound) ? ' on' : ''}">
            <button class="btn sm ghost" data-hear="${esc(x.file)}">▶</button><span class="grow">${esc(x.name)}</span><button class="btn sm" data-use="${esc(x.file)}">${t('Use')}</button></div>`).join('')}</div>
        <div class="row edbtns"><button class="btn sm eddanger" id="edsdel"><svg class="i"><use href="#i-trash"/></svg>${t('Remove')}</button></div>`;
      $('#edhear', box).onclick = () => pv.hear(pv.sfxUrl(q));
      edNumBind(box, {id: 'sfxdb', min: -12, max: 12, step: 1, dflt: 0,
        commit: v => push({op: 'sfx', f: q.f, kind: q.kind, db: v}, t('{sound} at {at}: {db} dB', {sound: edKind(q.kind), at: tcf(q.f), db: `${v > 0 ? '+' : ''}${v}`}))});
      $$('[data-hear]', box).forEach(b => b.onclick = () => pv.hear(b.dataset.hear === 'made-up' ? `/api/editor/sound?kind=${encodeURIComponent(q.kind)}` : edSoundUrl(b.dataset.hear)));
      $$('[data-use]', box).forEach(b => b.onclick = () => push({op: 'sfx', f: q.f, kind: q.kind, sound: b.dataset.use},
        t('{sound} at {at}: another sound', {sound: edKind(q.kind), at: tcf(q.f)})));
      $('#edsdel', box).onclick = () => delSel();
      return;
    }
    return capsInsp(box, S);
  }
  // ---------------------------------------------------------------- the captions: all of them in one list
  // (2026-10-27, the user: "improve the way we can modify the captions from a video all at the same time directly
  // instead of one clip at a time" - after Shotcut's / Premiere's / Resolve's caption lists: a row per caption, its
  // words typed in place; Enter between two words splits it there (each word keeps its frames), Enter at its end = the
  // next one, Backspace at its start joins it to the one before; Find & replace, the case and "Edit as text" change
  // them all as one change; the row under the playhead is followed. Style = the captions graphic's look, for all.)
  let capTab = (() => { try { return localStorage.getItem('ml.editor.captab') || 'words'; } catch (e) { return 'words'; } })();
  let capFind = '', capRepl = '', capText = null, capGo = null, capSkip = false, inspFocused = false, capT = 0;
  const capCaret = {};
  const capFollowOn = () => { try { return localStorage.getItem('ml.editor.capfollow') !== '0'; } catch (e) { return true; } };
  const capRows = () => (cur ? cur.captions.filter(c => !c.tail).sort((a, b) => a.f - b.f || a.cue - b.cue) : []);
  const capId = c => `${c.graphic}|${c.cue}`;
  const capDir = id => (cur.graphics.find(g => g.id === id) || {}).dir;
  const capAfterGone = (x, prev, next) => () => {             // the caption the panel shows once x is gone
    sel = prev ? {k: 'cap', graphic: prev.graphic, cue: prev.cue}
      : next ? {k: 'cap', graphic: next.graphic, cue: capDir(next.graphic) === capDir(x.graphic) ? next.cue - 1 : next.cue} : null; };
  const capRx = q => new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
  const capWords = v => String(v || '').split(/\s+/).filter(Boolean).join(' ');
  const CAP_CASES = () => [['upper', 'ABC', t('ALL CAPITALS')], ['lower', 'abc', t('all small letters')], ['sentence', 'Abc', t('A capital at the start of each sentence')]];
  const capCase = (v, k) => (k === 'upper' ? v.toLocaleUpperCase() : k === 'lower' ? v.toLocaleLowerCase()
    : v.toLocaleLowerCase().replace(/(^|[.!?]\s+)(\p{L})/gu, (m, a, b) => a + b.toLocaleUpperCase()));
  function capsInsp(box, S) {
    let c = S.captions.find(x => x.graphic === sel.graphic && x.cue === sel.cue);
    if (!c) { const R = capRows(); c = R.find(q => q.f + q.len - 1 >= prevF) || R[R.length - 1];
      if (!c) { sel = null; return drawInsp(); }
      sel = {k: 'cap', graphic: c.graphic, cue: c.cue}; }
    const g = S.graphics.find(x => x.id === c.graphic), fo = g ? S.folders[g.dir] || {} : {}, all = fo.settings || [];
    const sty = ED_CAP_STYLE.map(id => all.find(s => s.id === id)).filter(Boolean), cols = all.filter(s => s.type === 'color');
    const rest = all.filter(s => !ED_CAP_STYLE.includes(s.id) && s.type !== 'color'), LK = fo.looks || {};
    const lookOn = id => g && Object.entries(LK[id].values || {}).every(([k, v]) => !(k in g.values) || String(g.values[k]) === String(v));
    const rows = capRows(), hit = x => !!capFind && capRx(capFind).test(x.text), hits = rows.filter(hit);
    const row = x => `<div class="edcr${capId(x) === capId(c) ? ' on' : ''}${hit(x) ? ' hit' : ''}" data-cap="${esc(capId(x))}">
      <div class="edcrh"><button class="edct mono" data-seek="${x.f}" title="${ta('Go there')}">${esc(tcf(x.f))}</button><span class="grow"></span>
        <button class="edca" data-csplit title="${ta('Split it at the cursor (Enter) - or at the playhead')}">✂</button>
        <button class="edca" data-cmerge${x.next_here ? '' : ' disabled'} title="${x.next_here ? ta('Join it with the next one') : ta('The next caption is said in another shot')}">⤓</button>
        <button class="edca" data-cdel title="${ta('Remove this caption')}"><svg class="i"><use href="#i-trash"/></svg></button></div>
      <textarea class="edcx" rows="1" maxlength="300" spellcheck="true" data-fid="cap:${esc(capId(x))}" aria-label="${ta('Caption at {at}', {at: tcf(x.f)})}">${esc(x.text)}</textarea></div>`;
    const tabs = [['words', t('Words')], ['style', t('Style')]];
    const lines = capText == null ? 0 : capText.split('\n').length;
    box.innerHTML = `<div class="edih"><span class="eddot cap"></span><b>${t('Captions')}</b><span class="small muted">${tn(rows.length, '{n} caption', '{n} captions')}</span></div>
      <div class="edstabs" role="tablist">${tabs.map(([k, l]) => `<button role="tab" data-ctab="${k}" class="${capTab === k ? 'on' : ''}" aria-selected="${capTab === k}">${esc(l)}</button>`).join('')}</div>
      <div${capTab === 'words' ? '' : ' hidden'}>
        <div class="edctop"><div class="edcfind"><input type="search" id="edcf" placeholder="${ta('Find…')}" value="${esc(capFind)}" data-fid="capfind">
          <input type="text" id="edcrp" placeholder="${ta('Replace with…')}" value="${esc(capRepl)}" data-fid="caprepl">
          <button class="btn sm" id="edcra"${hits.length ? '' : ' disabled'} title="${ta('In every caption that has it - one change')}">${t('Replace all')}</button></div>
        <div class="small muted edcn" id="edcn">${capFind ? tn(hits.length, '{n} caption has it', '{n} captions have it') : ''}</div>
        <div class="edcbar"><span class="edchips">${CAP_CASES().map(([k, l, tip]) => `<button data-case="${k}" title="${ta('Every caption: {how}', {how: tip})}">${l}</button>`).join('')}</span>
          <label class="small edcfol"><input type="checkbox" id="edcfol"${capFollowOn() ? ' checked' : ''}> ${t('Follow the playhead')}</label>
          <button class="btn sm ghost" id="edcmode">${capText == null ? t('Edit as text') : t('As a list')}</button></div></div>
        ${capText == null ? `<div class="edcl" id="edcl">${rows.map(row).join('')}</div>
          <div class="small muted edchelp">${t('Enter between two words splits a caption there, Enter at its end goes to the next one; Backspace at its start joins it to the one before; Esc = as it was. Drag a caption on the timeline to change its timing.')}</div>`
        : `<textarea id="edctext" class="edctext" spellcheck="true" data-fid="captext">${esc(capText)}</textarea>
          <div class="small ${lines === rows.length ? 'muted' : 'amber'}" id="edctinfo">${lines === rows.length ? t('One line per caption, in order - an empty line removes it.') : t('{lines} lines for {n} captions - keep one line per caption (split or join them in the list).', {lines, n: rows.length})}</div>
          <div class="row edbtns"><button class="btn sm pri" id="edctapply">${t('Apply')}</button><button class="btn sm ghost" id="edctcancel">${t('Cancel')}</button></div>`}
      </div>
      <div${capTab === 'style' ? '' : ' hidden'}>${g ? `<div class="small muted">${t('For all the captions.')}</div>
        ${Object.keys(LK).length ? `<div class="edlbl">${t('Looks')}</div><div class="edchips edlooks">${Object.keys(LK).map(id => `<button data-look="${esc(id)}" class="${lookOn(id) ? 'on' : ''}" title="${esc(t(LK[id].what || ''))}">${esc(t(LK[id].label || id))}</button>`).join('')}</div>` : ''}
        ${setRows(g, sty)}
        ${cols.length ? `<details class="edsec" data-sec="cap.colours" open><summary>${t('Colours')}</summary>${setRows(g, cols)}</details>` : ''}
        ${rest.length ? `<details class="edsec" data-sec="cap.more"><summary>${t('More settings')}</summary>${setRows(g, rest)}</details>` : ''}` : ''}</div>`;
    $$('[data-ctab]', box).forEach(b => b.onclick = () => { capTab = b.dataset.ctab; try { localStorage.setItem('ml.editor.captab', capTab); } catch (e) { /* private window */ } drawInsp(); });
    $$('[data-look]', box).forEach(b => b.onclick = () => { if (b.classList.contains('on')) return;
      push({op: 'look', graphic: g.id, look: b.dataset.look}, t('Captions: the look “{look}”', {look: t(LK[b.dataset.look].label || b.dataset.look)})); });
    if (g) bindSets(box, g);
    const many = (edits, label) => (edits.length ? push({op: 'captions', edits}, label) : Promise.resolve(false));
    // find & replace: the rows that have it are marked as you type; Replace all = one change
    const cf = $('#edcf', box), cr = $('#edcrp', box);
    cf.oninput = () => { capFind = cf.value; const n = rows.filter(hit).length;
      $$('.edcr', box).forEach(r => { const x = rows.find(q => capId(q) === r.dataset.cap); r.classList.toggle('hit', !!x && hit(x)); });
      $('#edcn', box).textContent = capFind ? tn(n, '{n} caption has it', '{n} captions have it') : ''; $('#edcra', box).disabled = !n; };
    cf.onkeydown = e => { if (e.key !== 'Enter') return; e.preventDefault();      // Enter = the next caption that has it
      const hs = $$('.edcr.hit', box); if (!hs.length) return;
      const i = hs.findIndex(r => r.classList.contains('cur')); hs.forEach(r => r.classList.remove('cur'));
      const r = hs[(i + 1) % hs.length]; r.classList.add('cur'); r.scrollIntoView({block: 'nearest'});
      const x = rows.find(q => capId(q) === r.dataset.cap); if (x && pv) pv.seek(x.f); };
    cr.oninput = () => { capRepl = cr.value; };
    $('#edcra', box).onclick = () => { if (!capFind) return;
      const edits = rows.filter(hit).map(x => ({graphic: x.graphic, cue: x.cue, text: capWords(x.text.replace(capRx(capFind), () => capRepl))})).filter((e, i) => e.text !== rows.filter(hit)[i].text);
      many(edits, t('Captions: “{a}” → “{b}” in {n}', {a: capFind, b: capRepl, n: edits.length})); };
    $$('[data-case]', box).forEach(b => b.onclick = () => {
      const edits = rows.map(x => ({graphic: x.graphic, cue: x.cue, text: capCase(x.text, b.dataset.case)})).filter((e, i) => e.text !== rows[i].text);
      if (!edits.length) return toast(t('Every caption is like that already'));
      many(edits, t('Captions: {how}', {how: (CAP_CASES().find(q => q[0] === b.dataset.case) || [])[2]})); });
    $('#edcfol', box).onchange = e => { try { localStorage.setItem('ml.editor.capfollow', e.target.checked ? '1' : '0'); } catch (x) { /* private window */ } capsFollow(true); };
    $('#edcmode', box).onclick = () => { capText = capText == null ? rows.map(x => x.text).join('\n') : null; drawInsp(); };
    if (capText != null) {                                   // one line per caption: changed lines = one change
      const tx = $('#edctext', box), info = $('#edctinfo', box);
      tx.oninput = () => { capText = tx.value; const n = tx.value.split('\n').length, ok = n === rows.length;
        info.className = `small ${ok ? 'muted' : 'amber'}`; info.textContent = ok ? t('One line per caption, in order - an empty line removes it.')
          : t('{lines} lines for {n} captions - keep one line per caption (split or join them in the list).', {lines: n, n: rows.length}); };
      $('#edctcancel', box).onclick = () => { capText = null; drawInsp(); };
      $('#edctapply', box).onclick = () => { const L = tx.value.split('\n');
        if (L.length !== rows.length) return toast(t('{lines} lines for {n} captions - keep one line per caption (split or join them in the list).', {lines: L.length, n: rows.length}), 'err');
        const edits = rows.map((x, i) => ({graphic: x.graphic, cue: x.cue, text: capWords(L[i])})).filter((e, i) => e.text !== rows[i].text);
        if (!edits.length) { capText = null; return drawInsp(); }
        many(edits, tn(edits.length, 'Captions: {n} changed as text', 'Captions: {n} changed as text')).then(ok => { if (ok) { capText = null; drawInsp(); } }); };
      return;
    }
    // the rows
    const commit = (x, tx) => { const v = capWords(tx.value);
      if (v === x.text) return Promise.resolve(true);
      const i = rows.findIndex(q => capId(q) === capId(x));
      return push({op: 'caption', graphic: x.graphic, cue: x.cue, text: v}, v ? t('Caption at {at}: “{words}”', {at: tcf(x.f), words: v}) : t('Caption at {at} removed', {at: tcf(x.f)}),
        v ? null : capAfterGone(x, rows[i - 1], rows[i + 1])); };
    const rowOf = x => $(`.edcr[data-cap="${CSS.escape(capId(x))}"]`, box);
    const go = (x, caret) => { const r = x && rowOf(x); if (!r) return; const tx = $('textarea', r); tx.focus(); r.scrollIntoView({block: 'nearest'});
      const n = caret === 'end' ? tx.value.length : caret ?? 0; tx.setSelectionRange(n, n); };
    const splitAt = async (x, tx, pos) => {
      const toks = [...tx.value.matchAll(/\S+/g)], i = toks.filter(m => m.index + m[0].length <= pos).length;
      if (i <= 0 || i >= toks.length) return toast(t('Put the cursor between two words'), 'err');
      capSkip = true;
      if (!await commit(x, tx)) { capSkip = false; return; }
      const y = cur.captions.find(q => q.graphic === x.graphic && q.cue === x.cue && !q.tail);
      capSkip = false;
      if (!y || !y.wf || i >= y.wf.length) return;
      const at = y.wf[i], piece = cur.graphics.find(q => q.dir === capDir(x.graphic) && q.start <= at && at <= q.end) || {id: x.graphic};
      capGo = {dir: capDir(x.graphic), cue: x.cue + 1, caret: 0};
      push({op: 'capsplit', graphic: piece.id, cue: x.cue, at}, t('Caption at {at}: split at {to}', {at: tcf(y.f), to: tcf(at)}));
    };
    const merge = async (a, b, tx) => {                      // b joins a (a = the one before)
      capSkip = true;
      const ok = await commit(tx === undefined ? a : b, tx || $('textarea', rowOf(a)));
      capSkip = false;
      if (!ok) return;
      const y = cur.captions.find(q => q.graphic === a.graphic && q.cue === a.cue && !q.tail);
      capGo = {dir: capDir(a.graphic), cue: a.cue, caret: y ? y.text.length + 1 : 'end'};
      push({op: 'capmerge', graphic: a.graphic, cue: a.cue}, t('Captions at {at} and {to} as one', {at: tcf(a.f), to: tcf(b.f)}),
        () => { sel = {k: 'cap', graphic: a.graphic, cue: a.cue}; });
    };
    rows.forEach((x, i) => {
      const r = rowOf(x);
      if (!r) return;
      const tx = $('textarea', r), prev = rows[i - 1], next = rows[i + 1];
      const keep = () => { capCaret[capId(x)] = tx.selectionStart; };
      tx.onkeyup = tx.onclick = tx.onselect = keep;
      tx.onfocus = () => { $$('.edcr.on', box).forEach(q => q.classList.remove('on')); r.classList.add('on');
        if (sel.graphic !== x.graphic || sel.cue !== x.cue) { sel = {k: 'cap', graphic: x.graphic, cue: x.cue}; drawTL(); }
        if (pv && (prevF < x.f || prevF > x.f + x.len - 1)) pv.seek(x.f); };
      tx.onblur = () => { if (!capSkip) commit(x, tx); };
      tx.onkeydown = e => {
        if (e.isComposing) return;
        const p0 = tx.selectionStart, p1 = tx.selectionEnd, end = tx.value.trimEnd().length;
        if (e.key === 'Enter') { e.preventDefault();
          if (p0 === p1 && p0 > 0 && p0 < end) return splitAt(x, tx, p0);
          capSkip = true; commit(x, tx).then(ok => { capSkip = false; if (ok && next) go(next, 'end'); }); }
        else if (e.key === 'Tab') { e.preventDefault(); const to = e.shiftKey ? prev : next; if (to) go(to, 'end'); else tx.blur(); }
        else if (e.key === 'Escape') { e.preventDefault(); tx.value = x.text; capSkip = true; tx.blur(); capSkip = false; }
        else if (e.key === 'Backspace' && p0 === 0 && p1 === 0 && prev && prev.next_here) { e.preventDefault(); merge(prev, x, tx); }
        else if (e.key === 'Delete' && p0 === p1 && p0 >= end && next && x.next_here) { e.preventDefault(); capSkip = true;
          commit(x, tx).then(ok => { capSkip = false; if (ok) { capGo = {dir: capDir(x.graphic), cue: x.cue, caret: capWords(tx.value).length + 1};
            push({op: 'capmerge', graphic: x.graphic, cue: x.cue}, t('Captions at {at} and {to} as one', {at: tcf(x.f), to: tcf(next.f)})); } }); }
        else if (e.key === 'ArrowUp' && p0 === 0 && p1 === 0 && prev) { e.preventDefault(); go(prev, 'end'); }
        else if (e.key === 'ArrowDown' && p0 === p1 && p0 >= tx.value.length && next) { e.preventDefault(); go(next, 0); }
      };
      $('[data-seek]', r).onclick = () => { if (pv) pv.seek(x.f); tx.focus(); };
      $('[data-csplit]', r).onclick = () => { const pos = capCaret[capId(x)];
        if (pos > 0 && pos < tx.value.trimEnd().length) return splitAt(x, tx, pos);
        if (prevF > x.f && prevF <= x.f + x.len - 1) return push({op: 'capsplit', graphic: x.graphic, cue: x.cue, at: prevF}, t('Caption at {at}: split at {to}', {at: tcf(x.f), to: tcf(prevF)}));
        toast(t('Put the cursor between two words - or the playhead inside the caption'), 'err'); };
      $('[data-cmerge]', r).onclick = () => { if (next && x.next_here) { capGo = {dir: capDir(x.graphic), cue: x.cue, caret: 'end'};
        push({op: 'capmerge', graphic: x.graphic, cue: x.cue}, t('Captions at {at} and {to} as one', {at: tcf(x.f), to: tcf(next.f)})); } };
      $('[data-cdel]', r).onclick = () => { capSkip = true; push({op: 'caption', graphic: x.graphic, cue: x.cue, text: ''}, t('Caption at {at} removed', {at: tcf(x.f)}),
        capAfterGone(x, prev, next)).then(() => { capSkip = false; }); };
    });
    if (capGo) { const y = rows.find(q => q.cue === capGo.cue && capDir(q.graphic) === capGo.dir), r = y && rowOf(y);
      if (r) { const tx = $('textarea', r), n = capGo.caret === 'end' ? tx.value.length : Math.min(tx.value.length, capGo.caret);
        tx.focus({preventScroll: true}); tx.setSelectionRange(n, n); r.scrollIntoView({block: 'nearest'}); inspFocused = true; }
      capGo = null; }
    else if (capFocus) { const how = capFocus, r = rowOf(c); capFocus = false;
      if (r) { if (how === true) { const tx = $('textarea', r); tx.focus({preventScroll: true}); tx.select(); }
        r.scrollIntoView({block: 'center'}); inspFocused = true; } }
    capsFollow(true, inspFocused);
  }
  function capsFollow(now, stay) {                           // the row under the playhead (a few times a second while playing)
    const list = $('#edcl', el);
    if (!list || !cur) return;
    const t0 = performance.now();
    if (!now && pv && pv.playing && t0 - capT < 150) return;
    capT = t0;
    const x = capRows().find(q => q.f <= prevF && prevF <= q.f + q.len - 1), id = x ? capId(x) : '';
    $$('.edcr', list).forEach(r => r.classList.toggle('now', r.dataset.cap === id));
    if (x && !stay && capFollowOn() && !list.contains(document.activeElement)) { const r = $(`.edcr[data-cap="${CSS.escape(id)}"]`, list); if (r) r.scrollIntoView({block: 'nearest'}); }
  }
  // a scene of a video made from zero (its full-frame graphic on the main track): its speed, split, delete - its
  // edges and place dragged on the timeline like a shot's - then its graphic's own words, colours and settings
  // a shot's Video tab: a row per property - its value at the playhead, ◆ = a keyframe here, ◀ ▶ = the keys before /
  // after, ↺ = as it was; once a value has keys every change at the playhead is a key (auto-key)
  function keyRows(s) {
    const S = cur, d = drawOf(s.id) || {}, inShot = prevF >= s.start && prevF <= s.end, f = clamp(prevF, s.start, s.end), byFrame = [];
    return `<div class="edkeys2">${ED_KEY_PROPS().map(([p, label, unit, k, , dflt]) => {
      const sp = edKSpec(d, p), fbf = typeof sp === 'string' || (!!sp && typeof sp === 'object' && !Array.isArray(sp.keys)), [mn, mx, st] = edKRange(p, S);
      if (fbf) { byFrame.push(label);                      // (a shake draws it frame by frame: no keys over it)
        return edNum({id: 'k:' + p, label, value: dflt * k, min: mn, max: mx, step: st, unit, disabled: true, changed: false,
          tip: t('An effect moves it frame by frame here (a shake) - remove that effect in Effects to key it')}); }
      const ks = edKKeys(d, p), v = edCurve(sp, S.curves, dflt)(f), here = !!ks && ks.some(x => x[0] === prevF);
      const prev = ks && ks.filter(x => x[0] < prevF && x[0] >= s.start).pop(), next = ks && ks.find(x => x[0] > prevF && x[0] <= s.end);
      const keys = `<span class="ednk">${ks ? `<button class="edkn" data-kn="-1"${prev ? '' : ' disabled'} title="${ta('The keyframe before')}">◀</button>` : ''}<button class="edkd${here ? ' on' : ks ? ' has' : ''}" data-kd${inShot ? '' : ' disabled'} title="${here ? ta('Remove this keyframe') : ta('Add a keyframe here')}">◆</button>${ks ? `<button class="edkn" data-kn="1"${next ? '' : ' disabled'} title="${ta('The keyframe after')}">▶</button>` : ''}</span>`;
      return edNum({id: 'k:' + p, label, value: +(v * k).toFixed(unit === 'px' ? 0 : 1), min: mn, max: mx, step: st, unit, dflt: dflt * k,
        cls: ks ? 'keyed' : '', disabled: !!ks && !inShot, changed: !!ks || Math.abs(v - dflt) > 1e-6, after: keys}); }).join('')}</div>
      ${byFrame.length ? `<div class="small amber">${esc(t('{props}: an effect moves them frame by frame (a shake) - remove it in Effects to key them.', {props: byFrame.join(', ')}))}</div>` : ''}
      <div class="small muted">${inShot ? t('◆ adds a keyframe at the playhead; after that, a change at another moment adds the next.') : t('Move the playhead onto the shot to add keyframes.')}</div>`;
  }
  function bindKeys(box, s) {
    const d = drawOf(s.id);
    if (!d) return;
    const fNow = () => clamp(prevF, s.start, s.end);
    ED_KEY_PROPS().forEach(([p, lab, unit, k, , dflt]) => {
      const r = $(`[data-num="k:${p}"]`, box);
      if (!r || $('.ednv', r).disabled && !$('[data-kd]', r)) return;
      const [mn, mx, st, hmn, hmx] = edKRange(p, cur), spec0 = edKSpec(d, p), f = fNow();
      const shown = v => `${numLoc(+(v * k).toFixed(unit === 'px' ? 0 : 1))}${unit}`;
      const back = () => { edKSet(d, p, spec0); if (pv) pv.render(prevF, true); };
      edNumBind(box, {id: 'k:' + p, min: mn, max: mx, step: st, hardMin: hmn, hardMax: hmx, dflt: dflt * k,
        live: v => liveKey(d, p, f, v / k, spec0), revert: back,
        commit: v => push({op: 'kset', shot: s.id, prop: p, f: fNow(), value: v / k}, t('Shot {n}: {prop} {v}', {n: s.n, prop: lab, v: shown(v / k)})).then(ok => { if (!ok) back(); }),
        reset: () => push({op: 'kreset', shot: s.id, prop: p}, t('Shot {n}: {prop} back to how it was', {n: s.n, prop: lab}))});
      const kd = $('[data-kd]', r);
      if (kd) kd.onclick = () => { const ks = edKKeys(d, p), here = !!ks && ks.some(x => x[0] === prevF);
        push(here ? {op: 'kdel', shot: s.id, prop: p, f: prevF} : {op: 'kadd', shot: s.id, prop: p, f: prevF},
          here ? t('Shot {n}: the {prop} keyframe at {at} removed', {n: s.n, prop: lab, at: tcf(prevF)}) : t('Shot {n}: a {prop} keyframe at {at}', {n: s.n, prop: lab, at: tcf(prevF)})); };
      $$('[data-kn]', r).forEach(b => b.onclick = () => { const ks = edKKeys(d, p) || [];
        const g = +b.dataset.kn < 0 ? ks.filter(x => x[0] < prevF && x[0] >= s.start).pop() : ks.find(x => x[0] > prevF && x[0] <= s.end);
        if (g && pv) pv.seek(g[0]); });
    });
  }
  function liveKey(d, p, f, v, spec0) {                       // the preview only, while a value is dragged
    const ks = spec0 && typeof spec0 === 'object' && Array.isArray(spec0.keys) ? spec0.keys : null;
    if (ks) { const nk = ks.map(x => [...x]), i = nk.findIndex(x => x[0] === f);
      if (i >= 0) nk[i][1] = v; else { nk.push([f, v, 'smooth']); nk.sort((a, b) => a[0] - b[0]); }
      edKSet(d, p, {keys: nk}); }
    else edKSet(d, p, v);
    if (pv) pv.render(prevF, true);
  }
  function addTrans(shot, kind) {
    if (!cur || saving) return;
    const s = cur.shots.find(x => x.id === shot), K = (cur.trans_kinds || []).find(x => x[0] === kind);
    push({op: 'trans', shot, kind}, t('{transition} on the cut at {at}', {transition: edTrLabel(K ? K[1] : kind), at: tcf(s ? s.start : 0)}),
      () => { sel = {k: 'tr', id: shot}; });
  }
  function addTransNear(kind, f) { const c = nearCut(f); if (c) addTrans(c.id, kind); else toast(t('The video has no plain cut for a transition'), 'err'); }
  function sceneInsp(box, s, under) {
    const S = cur, g = S.graphics.find(x => x.id === s.id);
    if (!g) { box.innerHTML = ''; return; }
    const fo = S.folders[g.dir] || {}, all = fo.settings || [], words = new Set((g.words || []).map(w => w.key));
    const cols = all.filter(x => x.type === 'color'), wl = all.filter(x => words.has(x.id)), rest = all.filter(x => !words.has(x.id) && x.type !== 'color');
    box.innerHTML = `<div class="edih"><span class="eddot gfx"></span><b>${t('Scene {n}', {n: s.n})}</b><span class="small muted">${dec((s.end - s.start + 1) / S.fps)} s</span></div>
      <div class="small muted">${esc(edGfxName(g, S, lib))} · ${frange(s.start, s.end, S.fps)}</div>
      <div class="edlbl">${t('Speed')}</div>
      <div class="edchips">${ED_SPEEDS.map(x => `<button class="${Math.abs(x - s.speed) < 1e-6 ? 'on' : ''}" data-speed="${x}">${numLoc(x)}×</button>`).join('')}</div>
      <div class="row edbtns"><button class="btn sm" id="edsplit2"${!under ? ' disabled' : ''} title="${ta('Move the playhead inside the scene first')}">✂ ${t('Split at the playhead')}</button>
        <button class="btn sm eddanger" id="edshotdel"${S.shots.length < 2 ? ' disabled' : ''}><svg class="i"><use href="#i-trash"/></svg>${t('Delete')}</button></div>
      <div class="small muted">${t('Drag it to another place, its edges to make it shorter or longer - past its end it holds its last frame. What comes after moves with it.')}</div>
      ${wl.length ? `<div class="edlbl">${t('Its words')}</div>${setRows(g, wl)}` : ''}
      ${cols.length ? `<div class="edlbl">${t('Colours')}</div>${setRows(g, cols)}` : ''}
      ${rest.length ? `<details class="edmore"><summary>${t('More settings')}</summary>${setRows(g, rest)}</details>` : ''}`;
    $$('[data-speed]', box).forEach(b => b.onclick = () => { const x = +b.dataset.speed; if (Math.abs(x - s.speed) < 1e-6) return;
      push({op: 'speed', shot: s.id, speed: x}, t('Scene {n}: {x}× speed', {n: s.n, x: numLoc(x)})); });
    $('#edsplit2', box).onclick = () => splitHere();
    $('#edshotdel', box).onclick = () => delSel();
    bindSets(box, g);
  }
  // a shot's part of its clip (slip): shown live while the slider / Alt+drag moves, one change when let go
  const slipWords = d => !d ? t('as it is') : d > 0 ? tn(d, '{n} frame later', '{n} frames later') : tn(-d, '{n} frame earlier', '{n} frames earlier');
  function slipShow(s, d) {
    const x = pv && pv.S && pv.S.draw.find(q => q.t === 'clip' && q.id === s.id);
    if (!x) return;
    if (x._in0 == null) x._in0 = x.in;
    x.in = x._in0 + Math.round(d * (s.speed || 1));
    pv.render(clamp(pv.f, s.start, s.end), true);
  }
  const slipIt = (s, d) => push({op: 'slip', shot: s.id, by: d}, t('Shot {n}: {what} in its clip', {n: s.n, what: slipWords(d)}), () => { sel = {k: 'shot', id: s.id}; });
  // a clip of the video as a new shot: at the cut nearest the frame (3 s of it, or all of a shorter one)
  const placeAt = f => cur.shots.filter(s => (s.start + s.end) / 2 < f).length;
  function addClip(src, f) {
    if (!cur || saving || cur.timing_locked) return;
    const c = cur.clips.find(x => x.id === src);
    if (!c) return;
    const to = placeAt(f), len = Math.max(1, c.photo ? Math.round(3 * cur.fps) : Math.min(c.frames, Math.round(3 * cur.fps)));
    push({op: 'clipadd', src, in: 0, len, to}, t('{clip} added at place {k}', {clip: c.name, k: to + 1}), () => { const s = cur.shots[to]; if (s) sel = {k: 'shot', id: s.id}; });
  }
  // the song under the video: where it starts (seconds into it), its volume - one op on save (the song cut again)
  const songMax = () => { const p = (waves._song || {}).peaks || []; return p.length ? (p.length - cur.frames) / cur.fps : 0; };
  const songTime = s => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`;
  function setSong(start, db) {
    if (!cur || !cur.song || saving) return;
    const o = {op: 'song'};
    if (start != null) o.start = Math.round(clamp(start, 0, Math.max(0, songMax())) * 10) / 10;
    if (db != null) o.db = db;
    push(o, start != null ? t('The song: the video starts at {at} of it', {at: songTime(o.start)}) : t('The song: {db} dB', {db: `${db > 0 ? '+' : ''}${db}`}),
      () => { sel = {k: 'song'}; });
  }
  // ---------------------------------------------------------------- split, delete, add
  // ---------------------------------------------------------------- the safe zones, the right-click menu
  function applySafe() {                                     // (an upright video: the picker shows, the guides drawn)
    const sf = $('#edsafe', el), S = cur || base;
    if (!sf || !S) return;
    sf.hidden = !S.safe;
    if (!S.safe) { if (pv) pv.setSafe(null); return; }
    if (!sf.options.length) sf.innerHTML = `<option value="">${t('Safe zones: off')}</option>` + S.safe.map(z => `<option value="${esc(z.id)}">${esc(z.id === 'all' ? t('Safe zones: all three apps') : t('Safe zones: {app}', {app: z.label}))}</option>`).join('');
    const k = edSafeK();
    sf.value = S.safe.some(z => z.id === k) ? k : '';
    if (pv) pv.setSafe(S.safe.find(z => z.id === sf.value) || null);
  }
  // (2026-10-27, the user: "Right-click menu on the timeline (split, delete, duplicate, add a transition)": what the
  // editors put there - what was right-clicked is selected, its menu acts on it at the frame clicked; Esc / a click
  // outside close it, up / down move in it)
  let menu = null;
  const menuAway = e => { if (menu && !menu.contains(e.target)) closeMenu(); };
  const menuKey = e => {
    if (!menu) return;
    const bs = $$('button:not(:disabled)', menu), i = bs.indexOf(document.activeElement);
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closeMenu(); }
    else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation();
      if (bs.length) bs[(i + (e.key === 'ArrowDown' ? 1 : -1) + bs.length) % bs.length].focus(); }
    else if (!['Enter', ' ', 'Tab', 'Shift'].includes(e.key)) closeMenu();
  };
  function closeMenu() {
    if (!menu) return;
    menu.remove(); menu = null;
    document.removeEventListener('pointerdown', menuAway, true); document.removeEventListener('keydown', menuKey, true);
  }
  function openMenu(e) {
    e.preventDefault(); closeMenu();
    if (!cur || saving || busy) return;
    const it = e.target.closest('.edit'), f = fAt(e), k = it ? it.dataset.k : null, S = cur, lock = S.timing_locked, L = [];
    const item = (label, fn, o = {}) => L.push({label, fn, ...o}), sep = () => L.push('-');
    const at = g => { prevF = g; if (pv) pv.seek(g); };
    if (k === 'shot') {
      const s = S.shots.find(x => x.id === it.dataset.id);
      if (!s) return;
      sel = {k: 'shot', id: s.id};
      const i = S.shots.indexOf(s), cuts = plainCuts(), nx = S.shots[i + 1], has = id => (S.transitions || []).some(x => x.shot === id);
      item(t('Split here'), () => { at(f); splitHere(); }, {hint: 'S', off: lock || f <= s.start});
      item(t('Duplicate'), () => push({op: 'shotdup', shot: s.id}, t('Shot {n} duplicated', {n: s.n})), {off: lock || !!s.scene, tip: s.scene ? t('A scene is duplicated by Claude - ask for it') : ''});
      sep();
      if (cuts.some(c => c.id === s.id)) item(has(s.id) ? t('The transition before it…') : t('Add a transition before it'), () => { if (has(s.id)) { sel = {k: 'tr', id: s.id}; draw(); } else addTrans(s.id, 'mix'); });
      if (nx && cuts.some(c => c.id === nx.id)) item(has(nx.id) ? t('The transition after it…') : t('Add a transition after it'), () => { if (has(nx.id)) { sel = {k: 'tr', id: nx.id}; draw(); } else addTrans(nx.id, 'mix'); });
      if (S.sound === 'follows') { sep(); const m = s.db <= S.vol[0];
        item(m ? t('Sound on') : t('Mute'), () => push({op: 'volume', shot: s.id, db: m ? 0 : S.vol[0]}, m ? t('Shot {n}: its sound back on', {n: s.n}) : t('Shot {n}: muted', {n: s.n})), {off: lock}); }
      sep(); item(t('Delete'), () => delSel(), {hint: 'Del', off: lock || S.shots.length < 2, danger: true});
    } else if (k === 'gfx') {
      const g = S.graphics.find(x => x.id === it.dataset.id);
      if (!g) return;
      sel = {k: 'gfx', id: g.id};
      const fo = S.folders[g.dir] || {}, n = g.end - g.start + 1, f0 = g.end + n < S.frames ? g.end + 1 : Math.max(0, S.frames - n);
      item(t('Duplicate'), () => { const id = newId();
        push({op: 'gadd', id, template: fo.from, f: f0, len: Math.max(1, Math.min(n, S.frames - f0)), values: {...g.values}}, t('{graphic} duplicated at {at}', {graphic: edGfxName(g, S, lib), at: tcf(f0)}), () => { sel = {k: 'gfx', id}; }); },
        {off: !fo.from, tip: fo.from ? '' : t('Only a graphic made from a Motion Graphics template can be duplicated here')});
      sep(); item(t('Delete'), () => delSel(), {hint: 'Del', danger: true});
    } else if (k === 'cap') {
      const c = S.captions.find(x => x.graphic === it.dataset.g && x.cue === +it.dataset.cue);
      if (!c) return;
      sel = {k: 'cap', graphic: c.graphic, cue: c.cue};
      item(t('Edit its words'), () => { capFocus = true; draw(); });
      item(t('Split here'), () => push({op: 'capsplit', graphic: c.graphic, cue: c.cue, at: f}, t('Caption at {at}: split at {to}', {at: tcf(c.f), to: tcf(f)})),
        {off: !!c.tail || f <= c.f || f > c.f + c.len - 1});
      sep(); item(t('Delete'), () => delSel(), {hint: 'Del', danger: true});
    } else if (k === 'sfx') {
      const q = S.sfx[+it.dataset.i];
      if (!q) return;
      sel = {k: 'sfx', key: sfxOf(q)};
      const g = Math.min(S.frames - 1, q.f + Math.max(1, Math.round((q.len_s || 0.4) * S.fps)));
      item(t('Listen'), () => { if (pv) pv.hear(pv.sfxUrl(q)); });
      item(t('Duplicate'), () => push({op: 'sfxadd', f: g, kind: q.kind, ...(q.sound ? {sound: q.sound} : {}), ...(q.db ? {db: q.db} : {})}, t('{sound} added at {at}', {sound: edKind(q.kind), at: tcf(g)})));
      sep(); item(t('Delete'), () => delSel(), {hint: 'Del', danger: true});
    } else if (k === 'fx') {
      const x = (S.effects || []).find(q => q.id === it.dataset.id);
      if (!x) return;
      sel = {k: 'fx', id: x.id};
      item(t('Remove'), () => delSel(), {hint: 'Del', off: !x.can.includes('remove'), danger: true});
    } else if (k === 'tr') {
      const x = (S.transitions || []).find(q => q.shot === it.dataset.id);
      if (!x) return;
      sel = {k: 'tr', id: x.shot};
      item(t('Apply to all cuts'), () => push({op: 'transall', kind: x.kind, len: x.len, ...(x.dir ? {dir: x.dir} : {})}, t('{transition} on all {n} cuts', {transition: edTrLabel(x.label), n: plainCuts().length})));
      sep(); item(t('Remove'), () => delSel(), {hint: 'Del', danger: true});
    } else if (k === 'key') {
      sel = {k: 'key', id: it.dataset.s, f: +it.dataset.f};
      item(t('Remove this keyframe'), () => delSel(), {hint: 'Del', danger: true});
    } else if (k === 'seg') {                                // 0.6.1: a part of an edit by segments
      const s = segs && segs.segments.find(x => x.n === +it.dataset.n);
      if (!s) return;
      sel = {k: 'seg', id: s.n};
      item(t('back to the suggestion ({edit})', {edit: SEG_T()[segSug(s).t] || segSug(s).t}), () => segChange({reset: String(s.n)}), {off: s.by !== 'user'});
    } else {                                                 // an empty place: at the frame clicked
      const s = shotAt(f), c = nearCut(f);
      item(t('Split here'), () => { at(f); splitHere(); }, {hint: 'S', off: !s || f <= s.start || lock});
      item(t('Add a transition at the nearest cut'), () => addTrans(c.id, 'mix'), {off: !c});
      if (capPieces().length) item(t('Add a caption here'), () => { at(f); addCaption(); }, {off: !capPieceAt(f) || !!capAt(f)});
    }
    while (L[0] === '-') L.shift();
    while (L[L.length - 1] === '-') L.pop();
    if (!L.length) return;
    if (it) draw();
    menu = document.createElement('div');
    menu.className = 'edmenu'; menu.setAttribute('role', 'menu');
    menu.innerHTML = L.map((x, i) => (x === '-' ? (L[i - 1] === '-' ? '' : '<hr>') : `<button type="button" role="menuitem" data-mi="${i}" class="${x.danger ? 'bad' : ''}"${x.off ? ' disabled' : ''}${x.tip ? ` title="${esc(x.tip)}"` : ''}><span>${esc(x.label)}</span>${x.hint ? `<kbd>${esc(x.hint)}</kbd>` : ''}</button>`)).join('');
    document.body.appendChild(menu);
    const r = menu.getBoundingClientRect();
    menu.style.left = `${Math.max(4, Math.min(e.clientX, window.innerWidth - r.width - 6))}px`;
    menu.style.top = `${Math.max(4, Math.min(e.clientY, window.innerHeight - r.height - 6))}px`;
    $$('[data-mi]', menu).forEach(b => b.onclick = () => { const x = L[+b.dataset.mi]; closeMenu(); x.fn(); });
    document.addEventListener('pointerdown', menuAway, true); document.addEventListener('keydown', menuKey, true);
    const first = $('button:not(:disabled)', menu);
    if (first) first.focus({preventScroll: true});
  }
  function splitHere() {
    const s = shotAt(prevF);
    if (!s || s.start === prevF || cur.timing_locked) return;
    push({op: 'split', shot: s.id, at: prevF}, t('Shot {n} split at {at}', {n: s.n, at: tcf(prevF)}), () => { sel = null; });
  }
  // 0.6.1, an edit by segments' Parts lane (docs\plans.md *Edit by segments* step 6): a part's panel = its words, every
  // edit it can have (the pick lit), why, *yours* / back to the suggestion, *Apply to all like this*; a pick is saved at
  // once (POST .../segments - the picks, not this version) and *Build again with these picks* = the job segments_build:
  // a new version from the bare draft's cuts with every part as picked (what was changed here by hand is not in it).
  function segInsp(box) {
    const s = segs && segs.segments.find(x => x.n === sel.id);
    if (!s) { sel = null; return drawInsp(); }
    const T = SEG_T(), TIP = SEG_TIP(), b = segs.built, was = b && b.picks[s.n];
    const changed = !b || segs.segments.some(x => b.picks[x.n] !== x.pick);
    box.innerHTML = `<div class="edih"><span class="eddot seg t-${s.pick}"></span><b>${t('Part {n}', {n: s.n})}</b><span class="small muted">${dec((s.f1 - s.f0 + 1) / segs.fps)} s</span></div>
      <div class="small muted">${frange(s.f0, s.f1, segs.fps)}${s.topic ? ` · <b>${esc(s.topic)}</b>` : ''}</div>
      <div class="edsegw">${esc(segSay(s))}</div>
      <details class="edsec" data-sec="seg.edit" open><summary>${t('Its edit')}</summary>
        <div class="nesegc">${s.can.map(x => segChip(x, x === s.pick, x === s.pick ? segWhyOf(s) : esc(TIP[x] || ''), `data-st="${x}"`)).join('')}</div>
        <div class="small">${segWho(s, 'data-sreset')}${s.text ? ` <span class="nesegtx">“${esc(s.text.replace(/\|/g, ' / '))}”</span>` : ''}</div>
        ${s.like.length ? `<button class="btn sm" data-slike title="${ta('The parts MotionLab treated like this one get this edit too')}">${tn(s.like.length, 'Apply to all like this ({n} more)', 'Apply to all like this ({n} more)')}</button>` : ''}
        ${was && was !== s.pick ? `<div class="small amber">${t('Built as {edit} - build again to see the change', {edit: T[was] || was})}</div>` : ''}</details>
      <div class="edsegb"><button class="btn pri" id="edsegbuild"${changed && !saving ? '' : ' disabled'}><svg class="i"><use href="#i-film"/></svg>${b ? t('Build again with these picks') : t('Build the edit')}</button>
        <div class="small muted">${t('A new version from the cuts of {version}, every part as picked.', {version: `v${String(segs.plan).replace(/\D/g, '')}`})}
          ${b ? t('What you changed here by hand is not in it.') : ''}</div>
        ${b && b.ok === false ? `<div class="small amber">${t('The last build has a part not as picked - see its log on the Jobs page.')}</div>` : ''}</div>`;
    $$('[data-st]', box).forEach(c => c.onclick = () => { if (!c.classList.contains('on')) segChange({set: {[s.n]: c.dataset.st}}); });
    const r = $('[data-sreset]', box); if (r) r.onclick = () => segChange({reset: String(s.n)});
    const l = $('[data-slike]', box); if (l) l.onclick = () => segChange({like: s.n});
    $('#edsegbuild', box).onclick = async () => {
      try { await api('/api/jobs', {kind: 'segments_build', args: {project: P.name, plan: segs.plan}, queue: true});
        toast(t('Your edit is being built - it shows up here when it is ready'), 'ok'); route(); }
      catch (e) { toast(e.message, 'err'); }
    };
  }
  async function segChange(body) {
    if (!segs) return;
    try { const Sg = await api(`/api/project/${enc}/segments`, {plan, ...body}); segs = Sg.segments && Sg.segments.length ? Sg : null; }
    catch (e) { toast(e.message, 'err'); return; }
    drawTL(); drawInsp();
  }
  function delSel() {
    if (!sel || !cur) return;
    if (sel.k === 'shot') { const s = cur.shots.find(x => x.id === sel.id); if (!s || cur.timing_locked || cur.shots.length < 2) return;
      push({op: 'delete', shot: s.id}, t('Shot {n} deleted ({range})', {n: s.n, range: `${tcf(s.start)} - ${tcf(s.end)}`}), () => { sel = null; }); }
    else if (sel.k === 'gfx') { const g = cur.graphics.find(x => x.id === sel.id); if (!g) return;
      push({op: 'gdelete', layer: g.id}, t('{graphic}: removed', {graphic: edGfxName(g, cur, lib)}), () => { sel = null; }); }
    else if (sel.k === 'sfx') { const q = cur.sfx.find(x => sfxOf(x) === sel.key); if (!q) return;
      push({op: 'sfx', f: q.f, kind: q.kind, to: null}, t('{sound} at {from}: removed', {sound: edKind(q.kind), from: tcf(q.f)}), () => { sel = null; }); }
    else if (sel.k === 'fx') { const x = (cur.effects || []).find(q => q.id === sel.id); if (!x || !x.can.includes('remove')) return;
      push({op: 'fxremove', id: x.id}, t('{effect} at {at}: removed', {effect: edFxLabel(x.label), at: tcf(x.f)}), () => { sel = null; }); }
    else if (sel.k === 'tr') { const x = (cur.transitions || []).find(q => q.shot === sel.id); if (!x) return;
      push({op: 'trans', shot: x.shot, kind: null}, t('Transition at {at}: removed', {at: tcf(x.cut)}), () => { sel = null; }); }
    else if (sel.k === 'key') { const s = cur.shots.find(x => x.id === sel.id), d = s && drawOf(s.id); if (!d) return;
      const props = ED_KEY_PROPS().map(x => x[0]).filter(p => (edKKeys(d, p) || []).some(k => k[0] === sel.f));
      if (props.length) push({op: 'kdel', shot: s.id, f: sel.f, props}, t('Shot {n}: the keyframe at {at} removed', {n: s.n, at: tcf(sel.f)}), () => { sel = {k: 'shot', id: s.id}; }); }
    else if (sel.k === 'cap') { const c = cur.captions.find(x => x.graphic === sel.graphic && x.cue === sel.cue); if (!c) return;
      push({op: 'caption', graphic: c.graphic, cue: c.cue, text: ''}, t('Caption at {at}: removed', {at: tcf(c.f)}), () => { sel = null; }); }
  }
  // a caption can be added where a captions graphic shows (a piece of it: the shot it is said in), not over another
  const capPieces = () => cur ? cur.graphics.filter(g => g.captions && !g.new) : [];
  const capPieceAt = f => capPieces().find(g => g.start <= f && f <= g.end);
  const capAt = f => cur.captions.find(c => c.f <= f && f <= c.f + c.len - 1);
  function addCaption() {
    const g = capPieceAt(prevF);
    if (!cur || saving || !g || capAt(prevF)) return;
    push({op: 'capadd', graphic: g.id, at: prevF, text: t('New caption')}, t('Caption added at {at}', {at: tcf(prevF)}), () => {
      const c = cur.captions.find(x => x.f === prevF);
      if (c) { sel = {k: 'cap', graphic: c.graphic, cue: c.cue}; capFocus = true; } });
  }
  const newId = () => { let k = 1; while (cur.graphics.some(g => g.id === `add${k}`) || ops.some(o => o.id === `add${k}`)) k++; return `add${k}`; };
  function addSound(file, kind, f) {
    if (!cur || saving) return;
    f = clamp(f, 0, cur.frames - 1);
    push({op: 'sfxadd', f, kind, ...(file && file !== 'made-up' ? {sound: file} : {})}, t('{sound} added at {at}', {sound: edKind(kind), at: tcf(f)}),
      () => { sel = {k: 'sfx', key: `${f}|${kind}`}; });
  }
  function addFx(kind, f) {
    if (!cur || saving) return;
    f = clamp(f, 0, cur.frames - 1);
    const A = ED_FX_ADD().find(x => x[0] === kind);
    push({op: 'fxadd', kind, f}, t('{effect} added at {at}', {effect: A ? A[1] : kind, at: tcf(f)}), () => { sel = null; });
  }
  function addTemplate(tid, f) {
    if (!cur || saving) return;
    const T = lib.find(x => x.id === tid);
    if (!T) return;
    f = clamp(f, 0, cur.frames - 1);
    const len = clamp(T.frames && T.fps ? Math.round(T.frames / T.fps * cur.fps) : Math.round(3 * cur.fps), 1, cur.frames - f);
    const values = {};
    if (cur.shots.length && (T.settings || []).some(s => s.id === 'background' && s.type === 'boolean')) values.background = false;   // over the video
    const id = newId();
    push({op: 'gadd', id, template: tid, f, len, values}, t('{graphic} added at {at}', {graphic: t(T.name), at: tcf(f)}), () => { sel = {k: 'gfx', id}; });
  }
  // ---------------------------------------------------------------- the panel on the left: add sounds and templates
  let addTab = 'clips', addQ = '', addKind = '', lastCtx = '';
  // where the playhead is, for the Add panel's "why not here" (motionlab\edfx availability: the engine's own reasons,
  // per shot and per cut - the user, 2026-10-26: "show why some effects or transitions cant be used ... so people know")
  const ctxShot = () => (cur || base).shots.find(s => !s.scene && s.start <= prevF && prevF <= s.end) || null;
  const ctxCut = () => { const S = cur || base, C = S.shots.slice(1).filter((s, i) => s.start === S.shots[i].end + 1);
    return C.length ? C.reduce((a, b) => (Math.abs(b.start - prevF) < Math.abs(a.start - prevF) ? b : a)) : null; };
  const ctxKey = () => `${addTab}|${(ctxShot() || {}).id}|${(ctxCut() || {}).id}|${(nearCut(prevF) || {}).id}`;
  function drawAdd() {
    const box = $('#edadd', el);
    if (!base) { box.innerHTML = ''; return; }
    const q = addQ.toLowerCase(), L = base.library, hasClips = !!(cur || base).clips.length;
    if (addTab === 'clips' && !hasClips) addTab = 'sfx';                  // (a video made from zero has no clips)
    let list = '';
    if (addTab === 'sfx') {
      const rec = L.recorded.filter(x => (!addKind || x.kind === addKind) && (!q || `${x.name} ${x.kind} ${edKind(x.kind)}`.toLowerCase().includes(q)));
      const made = L.kinds.filter(k => (!addKind || k === addKind) && (!q || `${k} ${edKind(k)}`.toLowerCase().includes(q)));
      list = `<div class="edlist">${rec.map(x => `<div class="edrow" draggable="true" data-sfile="${esc(x.file)}" data-kind="${esc(x.kind)}" title="${ta('Drag it onto the timeline, or + = at the playhead')}">
            <button class="btn sm ghost" data-hear="${esc(edSoundUrl(x.file))}">▶</button><span class="eddot" style="--h:${meHue(x.kind)}"></span><span class="grow edrn">${esc(x.name)}</span><span class="small muted">${x.len_s ? dec(x.len_s) + ' s' : ''}</span><button class="btn sm" data-add>+</button></div>`).join('')}
          ${made.length ? `<div class="edlbl">${t('Made-up sounds')}</div>${made.map(k => `<div class="edrow" draggable="true" data-sfile="made-up" data-kind="${esc(k)}">
            <button class="btn sm ghost" data-hear="/api/editor/sound?kind=${encodeURIComponent(k)}">▶</button><span class="eddot" style="--h:${meHue(k)}"></span><span class="grow edrn">${esc(edKind(k))}</span><button class="btn sm" data-add>+</button></div>`).join('')}` : ''}
          ${!rec.length && !made.length ? `<div class="small muted">${t('Nothing matches.')}</div>` : ''}</div>`;
    } else {
      const over = !!(cur && cur.shots.length);
      const T = lib.filter(x => !q || `${t(x.name)} ${x.name} ${x.kind} ${mkind(x.kind)} ${(x.tags || []).join(' ')}`.toLowerCase().includes(q));
      const card = x => `<div class="edtpl" draggable="true" data-tpl="${esc(x.id)}" title="${esc(t(x.what || ''))}"><img src="${fileUrl(x.folder + '/thumb.png')}" alt="" loading="lazy" draggable="false"><span>${esc(t(x.name))}</span><button class="btn sm" data-add>+</button></div>`;
      const a = T.filter(x => !x.scene), b = T.filter(x => x.scene);
      list = `<div class="edlist">${over ? `<div class="edlbl">${t('Over your video')}</div>` : ''}<div class="edtpls">${(over ? a : [...a, ...b]).map(card).join('')}</div>
        ${over && b.length ? `<div class="edlbl">${t('Full-screen moments')}</div><div class="edtpls">${b.map(card).join('')}</div>` : ''}
        ${!T.length ? `<div class="small muted">${lib.length ? t('Nothing matches.') : t('Loading the templates…')}</div>` : ''}</div>`;
    }
    const kinds = addTab === 'sfx' ? [...new Set([...L.recorded.map(x => x.kind), ...L.kinds])].sort((a, b) => edKind(a).localeCompare(edKind(b))) : [];
    if (addTab === 'clips') {
      const C = (cur || base).clips.filter(c => !q || c.name.toLowerCase().includes(q)), used = new Set((cur || base).shots.map(s => s.src));
      list = `<div class="edlist">${C.map(c => { const tr = thumbRel(c.id), mid = c.photo ? 0 : Math.round(c.frames / 2 / (cur || base).fps) * (cur || base).fps;
          return `<div class="edrow edclip" draggable="true" data-clip="${esc(c.id)}" title="${ta('Drag it onto the video, or + = at the cut by the playhead')}">
          ${tr ? `<img src="/api/thumb?video=${encodeURIComponent(tr)}&f=${mid}&fps=${(cur || base).fps}" alt="" loading="lazy" draggable="false">` : '<span class="edclipi"></span>'}
          <span class="grow edrn">${esc(c.name)}<span class="small muted">${c.photo ? t('photo') : `${dec(c.frames / (cur || base).fps)} s`}${used.has(c.id) ? ` · ${t('in the video')}` : ''}</span></span>
          <button class="btn sm" data-add${(cur || base).timing_locked ? ' disabled' : ''}>+</button></div>`; }).join('')}
        ${!C.length ? `<div class="small muted">${t('Nothing matches.')}</div>` : ''}</div>`;
    }
    if (addTab === 'tr') {
      const how = ED_TR_HOW(), K = ((cur || base).trans_kinds || []).filter(([k, l]) => !q || `${edTrLabel(l)} ${how[k] || ''} ${k}`.toLowerCase().includes(q));
      const S0 = cur || base, c = nearCut(prevF), has = c && (S0.transitions || []).find(x => x.shot === c.id);
      const none = c ? '' : !S0.shots.some(s => !s.scene) ? t('Transitions go between two clips - this video is made of graphics') : t('The video has no plain cut for a transition');
      list = `<div class="edat small${none ? ' bad' : ''}">${none ? esc(none) : esc(t('On the cut at {at}', {at: tcf(c.start)})) + (has ? ` · ${esc(t('replaces {transition}', {transition: edTrLabel(has.label)}))}` : '')}</div>
        <div class="edlist">${K.map(([k, l]) => `<div class="edrow${none ? ' off' : ''}" draggable="${none ? 'false' : 'true'}" data-trk="${k}"${none ? ' data-off="1"' : ''} title="${none ? esc(none) : ta('Drag it onto a cut, or + = the cut nearest the playhead')}">
          <span class="edtric">${ED_TR_ICON[k] || '◐'}</span><span class="grow edrn"><b>${esc(edTrLabel(l))}</b> <span class="small muted">${esc(how[k] || '')}</span></span><button class="btn sm" data-add${none ? ' disabled' : ''}>+</button></div>`).join('')}
        ${!K.length ? `<div class="small muted">${t('Nothing matches.')}</div>` : ''}</div>`;
    }
    if (addTab === 'fx') {
      const A = ED_FX_ADD().filter(([k, l, how]) => !q || `${l} ${how} ${k}`.toLowerCase().includes(q));
      const S0 = cur || base, noClip = !S0.shots.some(s => !s.scene), can = S0.fx_can || {}, sh = ctxShot();
      const why = k => edCap(noClip && ED_FX_CLIP.has(k) ? t('Works on a clip - this video is made of graphics')
        : sh ? ((can.shots || {})[sh.id] || {})[k] || '' : (can.none || {})[k] || '');
      list = `<div class="edat small">${esc(sh ? t('At the playhead: shot {n}', {n: sh.n}) : t('At the playhead: no clip'))} · <span class="mono">${esc(tcf(prevF))}</span></div>
        <div class="edlist">${A.map(([k, l, how]) => { const no = why(k);
          return `<div class="edrow${no ? ' off' : ''}" draggable="${no ? 'false' : 'true'}" data-fxk="${k}"${no ? ' data-off="1"' : ''} title="${no ? esc(no) : ta('Drag it onto the timeline, or + = at the playhead')}">
          <span class="eddot fx"></span><span class="grow edrn"><b>${esc(l)}</b> <span class="small muted">${esc(how)}</span>${no ? `<span class="edwhy">${esc(no)}</span>` : ''}</span><button class="btn sm" data-add${no ? ' disabled' : ''}>+</button></div>`; }).join('')}
        ${!A.length ? `<div class="small muted">${t('Nothing matches.')}</div>` : ''}</div>`;
    }
    // a rail of big icons, each its own colour (the user, 2026-10-26: "more presence ... instead of an overcrowded tab bar")
    const rail = [...(hasClips ? [['clips', 'i-film', t('Clips')]] : []), ['sfx', 'i-volume', t('Sounds')], ['gfx', 'i-motion', t('Graphics')],
      ['fx', 'i-zap', t('Effects')], ['tr', 'i-trans', t('Transitions')]];
    box.innerHTML = `<div class="edaddw"><nav class="edrail" aria-label="${ta('What to add')}">${rail.map(([k, ic, l]) => `<button data-tab="${k}" class="${addTab === k ? 'on' : ''}" title="${esc(l)}" aria-pressed="${addTab === k}"><svg class="i"><use href="#${ic}"/></svg><span>${esc(l)}</span></button>`).join('')}</nav>
      <div class="edaddb"><div class="edfind"><input type="search" id="edq" placeholder="${ta('Search…')}" value="${esc(addQ)}">${addTab === 'sfx' ? `<select id="edkind" title="${ta('Kind of sound')}"><option value="">${t('All kinds')}</option>${kinds.map(k => `<option value="${esc(k)}"${addKind === k ? ' selected' : ''}>${esc(edKind(k))}</option>`).join('')}</select>` : ''}</div>${list}</div></div>`;
    lastCtx = ctxKey();
    $$('[data-tab]', box).forEach(b => b.onclick = () => { addTab = b.dataset.tab; addQ = ''; drawAdd(); if (addTab === 'gfx' && !lib.length) loadLib(); });
    const qi = $('#edq', box);
    qi.oninput = debounce(() => { addQ = qi.value; const pos = qi.selectionStart; drawAdd(); const n = $('#edq', box); n.focus(); n.setSelectionRange(pos, pos); }, 200);
    const ks = $('#edkind', box);
    if (ks) ks.onchange = () => { addKind = ks.value; drawAdd(); };
    $$('[data-hear]', box).forEach(b => b.onclick = e => { e.stopPropagation(); if (pv) pv.hear(b.dataset.hear); });
    $$('.edrow', box).forEach(r => {
      if (r.dataset.clip) {                                  // a clip: a new shot at the cut by the playhead / where dropped
        $('[data-add]', r).onclick = () => addClip(r.dataset.clip, prevF);
        r.ondragstart = e => { e.dataTransfer.setData('text/x-ml-clip', r.dataset.clip); e.dataTransfer.effectAllowed = 'copy'; };
        return;
      }
      if (r.dataset.trk) {                                   // a transition: on the cut nearest the playhead / the drop
        if (r.dataset.off) return;
        $('[data-add]', r).onclick = () => addTransNear(r.dataset.trk, prevF);
        r.ondragstart = e => { e.dataTransfer.setData('text/x-ml-tr', r.dataset.trk); e.dataTransfer.effectAllowed = 'copy'; };
        return;
      }
      if (r.dataset.fxk) {                                   // an effect: at the playhead, or where it is dropped
        if (r.dataset.off) return;
        $('[data-add]', r).onclick = () => addFx(r.dataset.fxk, prevF);
        r.ondragstart = e => { e.dataTransfer.setData('text/x-ml-fx', r.dataset.fxk); e.dataTransfer.effectAllowed = 'copy'; };
        return;
      }
      $('[data-add]', r).onclick = () => addSound(r.dataset.sfile, r.dataset.kind, prevF);
      r.ondragstart = e => { e.dataTransfer.setData('text/x-ml-sfx', JSON.stringify({file: r.dataset.sfile, kind: r.dataset.kind})); e.dataTransfer.effectAllowed = 'copy'; };
    });
    $$('.edtpl', box).forEach(c => {
      $('[data-add]', c).onclick = () => addTemplate(c.dataset.tpl, prevF);
      c.ondragstart = e => { e.dataTransfer.setData('text/x-ml-tpl', c.dataset.tpl); e.dataTransfer.effectAllowed = 'copy'; };
    });
  }
  async function loadLib() {
    try { lib = ((await api('/api/motion')).library || []).filter(x => !x.problem); } catch (e) { lib = []; }
    if (addTab === 'gfx') drawAdd();
    drawTL(); drawInsp();
  }
  // ---------------------------------------------------------------- the top: undo / redo, the changes, save
  function drawTop() {
    $('#edundo', el).disabled = !ops.length || saving; $('#edredo', el).disabled = !redo.length || saving;
    const h = $('#edhist', el);
    h.disabled = !ops.length;
    h.innerHTML = `<svg class="i"><use href="#i-clock"/></svg>${ops.length ? tn(ops.length, '{n} change', '{n} changes') + ' ▾' : t('No changes yet')}`;
    if (!ops.length) histPop(false); else if (!$('#edpop', el).hidden) histPop(true);
    $('#edsave', el).disabled = !ops.length || saving;
    $('#eddel', el).disabled = !sel || saving || (sel.k === 'shot' && (cur.timing_locked || cur.shots.length < 2));
    $('#edhint', el).textContent = base && base.frames !== cur.frames ? t('Length: {was} → {now}', {was: `${dec(base.frames / cur.fps)} s`, now: `${dec(cur.frames / cur.fps)} s`}) : '';
  }
  function draw() { if (!cur) return; drawTop(); drawTL(); drawInsp(); }
  $('#edundo', el).onclick = undo; $('#edredo', el).onclick = redoIt;
  // the changes so far: a list under the button (no dialog), the newest last; Start again drops them all
  function histPop(open) {
    const pop = $('#edpop', el), h = $('#edhist', el);
    pop.hidden = !open; h.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (!open) return;
    pop.innerHTML = `<b>${t('Your changes')}</b><ol class="melist">${labels.map(l => `<li>${esc(l)}</li>`).join('')}</ol>
      <div class="small muted">${t('The version you started from stays. Only what changed is made again.')}</div>
      <div class="row" style="margin-top:8px"><button class="btn sm ghost" id="edundo2">↶ ${t('Undo')}</button><button class="btn sm ghost eddanger" id="edclear">${t('Start again')}</button></div>`;
    $('#edundo2', pop).onclick = () => undo();
    $('#edclear', pop).onclick = () => { histPop(false); preview([], []).then(() => { sel = null; draw(); }); };
  }
  $('#edhist', el).onclick = e => { e.stopPropagation(); histPop($('#edpop', el).hidden); };
  const popAway = e => { const pop = $('#edpop', el); if (pop && !pop.hidden && !pop.contains(e.target)) histPop(false); };
  document.addEventListener('click', popAway);
  onCleanup(() => document.removeEventListener('click', popAway));
  $('#edsave', el).onclick = async () => {
    const b = $('#edsave', el);
    b.disabled = true; await settle();
    if (!ops.length) { b.disabled = false; return; }
    try { const J = await api(`/api/project/${enc}/miniedit`, {plan, ops});
      // 2026-11-10 review: the changes were dropped here, before the job had made anything of them - a save that
      // failed or was taken off the queue lost them. They stay in this window's backup, marked with their job, and
      // come back as unsaved changes if it never makes the new version (loadPlan)
      try { if (J && J.id && J.args && J.args.changes) localStorage.setItem(store(), JSON.stringify({ops, labels, sig: planSig(base), job: J.id, ch: J.args.changes}));
        else localStorage.removeItem(store()); } catch (x) { /* private window */ }
      ops = []; labels = []; saving = true; if (pv) pv.pause();
      toast(t('Saving your changes as a new version - it shows here when it is ready.'), 'ok'); route(); }
    catch (e) { toast(e.message, 'err'); b.disabled = false; }    // (route: the page's progress panel follows the job)
  };
  $('#edsplit', el).onclick = splitHere; $('#eddel', el).onclick = delSel; $('#edcapadd', el).onclick = addCaption;
  // *See it rendered* (the plan: "before Save, a preview of the second around it"): the moment around the playhead with
  // the changes so far, rendered by the lab's own renderer (a job, picture only) and played over the preview
  $('#edrange', el).onclick = async () => {
    const box = $('#edrng', el), f = prevF, half = Math.round(cur.fps), a = Math.max(0, f - half), b = Math.min(cur.frames - 1, f + half);
    const show = (html) => { box.hidden = false; box.innerHTML = `<div class="row sp"><b class="small">${t('Rendered exactly')} · ${frange(a, b, cur.fps)}</b><button class="btn sm ghost" id="edrngx" title="${ta('Close')}">✕</button></div>${html}`;
      $('#edrngx', box).onclick = () => { box.hidden = true; box.innerHTML = ''; }; };
    let r;
    try { r = await api(`/api/project/${enc}/editor/range`, {plan, ops, a, b}); } catch (e) { toast(e.message, 'err'); return; }
    const play = () => show(`<video src="${fileUrl(r.out)}?v=${Date.now()}" autoplay loop muted playsinline></video><div class="small muted">${t('Picture only - the sound is made when you save.')}</div>`);
    if (r.ready) return play();
    show(`<div class="small muted edrngw">${t('Rendering the moment…')}</div>`);
    const tick = async () => {
      let j; try { j = await api(`/api/jobs/${r.job}?since=999999`); } catch (e) { setTimeout(tick, 1000); return; }
      if (['running', 'queued', 'cancelling'].includes(j.status)) { setTimeout(tick, 700); return; }
      if (j.status === 'done') play(); else show(`<div class="small bad">${t('The moment could not be rendered.')} ${reportBtn(j.id)}</div>`);
    };
    tick();
  };
  $('#edsnap', el).onclick = () => { snap = !snap; $('#edsnap', el).classList.toggle('on', snap); };
  const zoomTo = (z, keepF = prevF) => { const sc = $('#edscroll', el), x0 = keepF * pxf - sc.scrollLeft; zoom = clamp(z, 0, 100); $('#edzoom', el).value = zoom; drawTL(); sc.scrollLeft = Math.max(0, keepF * pxf - x0); };
  $('#edzoom', el).oninput = e => zoomTo(+e.target.value);
  $('#edzi', el).onclick = () => zoomTo(zoom + 12); $('#edzo', el).onclick = () => zoomTo(zoom - 12);
  $('#edscroll', el).addEventListener('wheel', e => { if (!e.ctrlKey) return; e.preventDefault(); const r = canvas().getBoundingClientRect();
    zoomTo(zoom + (e.deltaY < 0 ? 6 : -6), clamp(Math.round((e.clientX - r.left) / pxf), 0, cur.frames - 1)); }, {passive: false});
  $$('[data-tr]', el).forEach(b => b.onclick = () => { if (!pv) return; const a = b.dataset.tr;
    if (a === 'play') pv.toggle(); else if (a === 'start') pv.seek(0); else if (a === 'end') pv.seek(cur.frames - 1);
    else if (a === 'mute') { pv.mute(!pv.muted); b.textContent = pv.muted ? '🔇' : '🔊'; } else pv.seek(prevF + +a); });
  $('#edpvol', el).oninput = e => {
    const v = Math.pow(+e.target.value / 100, 2); edVolume(v); if (!pv) return;
    pv.setVolume(v);
    if (pv.muted && v > 0) { pv.mute(false); const b = $('[data-tr=mute]', el); if (b) b.textContent = '🔊'; }
  };
  el.addEventListener('mousedown', e => { if (e.target.closest('button')) e.preventDefault(); });   // the keys stay with the Editor
  const cv = $('#edcanvas', el);
  cv.addEventListener('pointerdown', onDown); cv.addEventListener('pointermove', onMove);
  cv.addEventListener('pointerup', onUp); cv.addEventListener('pointercancel', onUp);
  cv.addEventListener('dblclick', e => { const it = e.target.closest('.edit');
    if (it && it.dataset.k === 'cap') { sel = {k: 'cap', graphic: it.dataset.g, cue: +it.dataset.cue}; capFocus = true; draw(); } });
  cv.addEventListener('contextmenu', openMenu);
  $('#edsafe', el).onchange = e => { edSafeK(e.target.value); applySafe(); };
  cv.addEventListener('dragover', e => { if ([...e.dataTransfer.types].some(x => x.startsWith('text/x-ml-'))) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy';
    const ph = $('.edins', el); ph.hidden = false; ph.style.top = '0px'; ph.style.height = '100%';
    const tc0 = [...e.dataTransfer.types].includes('text/x-ml-tr') && nearCut(fAt(e));
    if (tc0) ph.style.left = `${tc0.start * pxf - 2}px`;                          // a transition: the cut it lands on
    else if ([...e.dataTransfer.types].includes('text/x-ml-clip') && cur.shots.length) {     // a clip goes into a cut
      const k = placeAt(fAt(e)), x = k < cur.shots.length ? cur.shots[k].start : cur.shots[cur.shots.length - 1].end + 1;
      ph.style.left = `${x * pxf - 2}px`; } else ph.style.left = `${fAt(e) * pxf - 1}px`; } });
  cv.addEventListener('dragleave', () => { const ph = $('.edins', el); if (ph) ph.hidden = true; });
  cv.addEventListener('drop', e => { e.preventDefault(); const ph = $('.edins', el); if (ph) ph.hidden = true;
    const f = fAt(e), s = e.dataTransfer.getData('text/x-ml-sfx'), tp = e.dataTransfer.getData('text/x-ml-tpl'), fk = e.dataTransfer.getData('text/x-ml-fx'), ck = e.dataTransfer.getData('text/x-ml-clip');
    const tk = e.dataTransfer.getData('text/x-ml-tr');
    if (s) { const o = JSON.parse(s); addSound(o.file, o.kind, f); } else if (tp) addTemplate(tp, f); else if (fk) addFx(fk, f); else if (ck) addClip(ck, f);
    else if (tk) addTransNear(tk, f); });
  cv.addEventListener('click', e => { const b = e.target.closest('.edcutb'); if (b && !saving) addTrans(b.dataset.cut, 'mix'); });
  // keys while the Editor is on screen (never while typing; the dialogs keep theirs)
  const onKey = e => {
    if (!cur || !pv || !el.isConnected || (e.target.matches && e.target.matches('input:not([type=range]):not([type=checkbox]):not([type=radio]):not([type=button]), textarea, select')) || !$('#modal').hidden) return;
    const k = e.key, ctrl = e.ctrlKey || e.metaKey;
    if (ctrl && (k === 'z' || k === 'Z')) { if (e.shiftKey) redoIt(); else undo(); }
    else if (ctrl && (k === 'y' || k === 'Y')) redoIt();
    else if (ctrl) return;
    else if (k === ' ') { if (pv) pv.toggle(); }
    else if (k === 'ArrowLeft' || k === 'ArrowRight') { if (pv) pv.seek(prevF + (k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1)); }
    else if (k === 'Home') { if (pv) pv.seek(0); } else if (k === 'End') { if (pv) pv.seek(cur.frames - 1); }
    else if (k === 's' || k === 'S') splitHere();
    else if (k === 'Delete' || k === 'Backspace') delSel();
    else if (k === 'Escape') { if (!$('#edpop', el).hidden) histPop(false); else { sel = null; draw(); } }
    else if (k === '+' || k === '=') zoomTo(zoom + 12); else if (k === '-') zoomTo(zoom - 12);
    else if (k === 'm' || k === 'M') { const b = $('[data-tr=mute]', el); if (b) b.click(); }
    else return;
    e.preventDefault();
  };
  document.addEventListener('keydown', onKey);
  const onResize = debounce(() => { if (cur) drawTL(); }, 150);
  window.addEventListener('resize', onResize);
  const spl = $('#edsplitter', el);                            // drag = the preview's height (remembered), double-click = as it was
  spl.onpointerdown = e => {
    if (e.button || !pv) return;
    e.preventDefault(); spl.setPointerCapture(e.pointerId); spl.classList.add('on');
    const y0 = e.clientY, h0 = pv.stage.getBoundingClientRect().height;
    spl.onpointermove = ev => { edPvH(clamp(h0 + ev.clientY - y0, 160, window.innerHeight - 220)); pv.fit(); };
    spl.onpointerup = spl.onpointercancel = () => { spl.onpointermove = spl.onpointerup = spl.onpointercancel = null; spl.classList.remove('on'); if (cur) drawTL(); };
  };
  spl.ondblclick = () => { edPvH(null); if (pv) pv.fit(); };
  // the side panels: wider / narrower by their inner edge, swapped left - right (edLayout; the preview fits itself to
  // what is left - its ResizeObserver)
  const mainEl = $('#edmain', el);
  const applyLayout = () => {
    const L = edLayout();
    mainEl.classList.toggle('swap', !!L.swap);
    $('#edswap', el).classList.toggle('on', !!L.swap);
    ['l', 'r'].forEach(k => { if (L[k]) mainEl.style.setProperty(`--ed${k}`, `${L[k]}px`); else mainEl.style.removeProperty(`--ed${k}`); });
  };
  applyLayout();
  $$('.edvsplit', el).forEach(h => {
    const k = h.dataset.side, panel = h.parentElement;
    h.onpointerdown = e => {
      if (e.button) return;
      e.preventDefault(); h.setPointerCapture(e.pointerId); h.classList.add('on');
      const x0 = e.clientX, w0 = panel.getBoundingClientRect().width, sign = (k === 'l') !== !!edLayout().swap ? 1 : -1;   // (on the left: right = wider)
      h.onpointermove = ev => { edLayout({[k]: Math.round(clamp(w0 + sign * (ev.clientX - x0), 220, Math.max(240, Math.min(620, window.innerWidth * 0.34))))}); applyLayout(); };
      h.onpointerup = h.onpointercancel = () => { h.onpointermove = h.onpointerup = h.onpointercancel = null; h.classList.remove('on'); };
    };
    h.ondblclick = () => { edLayout({[k]: null}); applyLayout(); };
  });
  $('#edswap', el).onclick = () => { edLayout({swap: !edLayout().swap}); applyLayout(); };
  onCleanup(() => { gone = true; closeMenu(); document.body.classList.remove('edwide'); document.removeEventListener('keydown', onKey); window.removeEventListener('resize', onResize); if (pv) { pv.destroy(); pv = null; } });
  brandData().then(() => { if (sel) drawInsp(); });
  api('/api/jobs').then(J => { saving = J.some(j => j.kind === 'miniedit' && (j.args || {}).project === P.name && ['running', 'queued'].includes(j.status)); if (cur) draw(); }).catch(() => {});
  const R = renderPicker($('#edpick', el), P, r => { load(r).then(() => { if (!gone && cur) drawAdd(); }); });
  if (!R.length && P.plans.length) loadPlan(P.plans[P.plans.length - 1].file).then(() => { if (!gone && cur) drawAdd(); });
  else if (!R.length) $('#edprev', el).innerHTML = `<div class="empty">${t('No render yet - the Editor changes a made version.')}</div>`;
  loadLib();
}

function projVersions(el, P) {
  const R = newestFirst(P), enc = encodeURIComponent(P.name);
  el.innerHTML = `<div class="hint" style="margin-bottom:12px">${t('Every version of this edit and its renders. A new version never replaces an old one. Rate the newest on the <a href="{link}">Review</a> tab.', {link: `#/project/${enc}/review`})}</div>
    <div class="panel"><h2>${t('Edit versions')}</h2><table class="t"><thead><tr><th>${t('Version')}</th><th>${t('Length')}</th><th>${t('Made|version')}</th><th class="num">${t('Layers')}</th></tr></thead><tbody>
    ${P.plans.slice().reverse().map(p => `<tr><td class="mono amber">${esc(p.version)}</td><td>${t('{frames} frames · {range} · {fps} fps', {frames: p.frames, range: frange(0, p.frames - 1, p.fps), fps: p.fps})}</td>
      <td class="small">${p.made_by === 'draft_edit.py' ? `${p.style ? t('quick draft: {style}', {style: esc(p.style)}) : t('quick draft')}${p.notes ? ` · <a href="#" data-open="${esc(p.notes)}">${t('notes')}</a>` : ''}` : `<span class="muted">${t('by Claude')}</span>`}</td>
      <td class="num">${p.layers}</td></tr>`).join('') || `<tr><td colspan="4" class="muted">${t('none yet - <b>New edit…</b> above')}</td></tr>`}</tbody></table>
    ${P.edit_scripts.length ? `<div class="small muted" style="margin-top:8px">${t('Edit scripts: {list}', {list: P.edit_scripts.map(s => `<a href="#" data-open="${esc(s)}" data-reveal>${esc(s.split('/').pop())}</a>`).join(', ')})}</div>` : ''}</div>
    <h3>${t('Renders')}</h3>
    ${R.length ? `<div class="grid g2">${R.map((r, i) => `<div class="panel"><div class="row sp"><h2>${renderLabel(r)} <span class="small muted">${r.kind === 'resolve' ? t('from DaVinci Resolve') : t('lab render')}</span></h2>
      <span class="small muted">${esc(r.name)} · ${bytes(r.size)} · ${esc(r.modified)}</span></div><div id="pl${i}"></div>
      <div class="row" style="margin-top:8px"><button class="btn sm" data-open="${esc(r.rel)}">${t('Open in player')}</button><button class="btn sm" data-open="${esc(r.rel)}" data-reveal>${t('Show in folder')}</button>
        <div class="grow"></div>${delBtn('file', r.rel, '', ' ' + t('Delete'))}</div></div>`).join('')}</div>` : `<div class="empty">${t('No renders yet.')}</div>`}
    ${P.compares.length ? `<h3>${t('Side by side with the reference')}</h3>
    <div class="grid g2">${P.compares.map((r, i) => `<div class="panel"><div class="row sp" style="margin-bottom:6px"><span class="small muted">${esc(r.name)} · ${bytes(r.size)}</span>${delBtn('file', r.rel, '', ' ' + t('Delete'))}</div><div id="cp${i}"></div></div>`).join('')}</div>` : ''}`;
  R.forEach((r, i) => new Player($('#pl' + i, el), r.rel, renderFps(P, r), renderFrames(P, r)));
  const fps0 = (P.plans[0] || {}).fps || 25, n0 = (P.plans[0] || {}).frames;
  P.compares.forEach((r, i) => new Player($('#cp' + i, el), r.rel, fps0, n0));
}
