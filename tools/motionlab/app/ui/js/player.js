/* MotionLab app - js/player.js: the video player and its formats, the Timeline, an analysis page's Overview and Content tabs.
   Split from app.js 2026-11-02: plain scripts sharing one scope, loaded in order by index.html - use any file's
   names inside functions; code that runs while the files load may use earlier files only (main.js starts the app). */
'use strict';
// ============================================================================================ player
// 0.4.2.1: HEVC (TikTok's best format) plays only where Windows has the HEVC Video Extension, AV1 / ProRes / MPEG-2
// often not at all: such a video gets a small H.264 copy for the player (job player_copy, .app\player\; the same
// frames at the same times, so frame numbers still match). The address ?player=copy forces it (tests on a PC that
// has the extension).
const FORCE_COPY = new URLSearchParams(location.search).get('player') === 'copy';
const CODEC_TYPE = {h264: 'avc1.640028', hevc: 'hvc1.1.6.L120.90', av1: 'av01.0.08M.08', vp9: 'vp09.00.40.08'};
const codecWord = c => ({hevc: 'HEVC', av1: 'AV1', h264: 'H.264', vp9: 'VP9', prores: 'ProRes', mpeg2video: 'MPEG-2'})[c] || (c ? String(c).toUpperCase() : '');
function browserPlays(c) {                            // c = /api/player: the codec ffprobe found (+ its tag)
  if (c.codec === 'vp8') return true;
  const k = CODEC_TYPE[c.codec];
  if (!k) return false;                               // ProRes, DNxHD, MPEG-2, old MPEG-4: no browser plays them
  const t = `video/mp4; codecs="${c.codec === 'hevc' && c.tag === 'hev1' ? k.replace('hvc1', 'hev1') : k}"`;
  return document.createElement('video').canPlayType(t) !== '' && (!window.MediaSource || MediaSource.isTypeSupported(t));
}
class Player {
  /* frame-accurate video: the shown frame comes from requestVideoFrameCallback (presented media time).
     0.4.3.5 (the user: "the controls are on the left, it's very hard to click play/pause and also to move to a specific
     point"): a click on the picture = play / pause (a big ▶ before the first play), a seek bar as wide as the video
     (drag it; the pointer shows the frame + timecode), the transport in the middle like an editor's viewer, the length,
     sound and full screen; keys when the player has the focus: Space, ← → (Shift = 10), Home / End, M, F */
  constructor(el, src, fps, frames, label = '') {
    this.fps = fps; this.N = frames || 1e9; this.frame = 0; this._range = null; this.fns = []; this.looping = false;
    const nf = 'tabindex="-1"';                              // the buttons never take the focus: the keys stay with the player
    el.innerHTML = `<div class="player" tabindex="0"><div class="pview"><video preload="auto" playsinline src="${fileUrl(src)}"></video>
        <span class="pflash" aria-hidden="true"></span><button class="pbig" data-a="play" ${nf} aria-label="${ta('Play')}">▶</button></div>
      <div class="pscrub" title="${ta('Click or drag to move')}"><div class="pstrack"><i class="psrange" hidden></i><i class="psfill"></i><i class="pshead"></i></div><span class="pstip" hidden></span></div>
      <div class="pbar">
        <div class="pbl"><span class="now">f0<span class="tc">00:00:00:00</span></span><span class="ptot"></span>${label ? `<span class="hint">${esc(label)}</span>` : ''}</div>
        <div class="pbc">
          <button class="btn" data-a="start" ${nf} title="${ta('First frame (Home)')}">⏮</button>
          <button class="btn" data-a="-10" ${nf} title="${ta('10 frames back (Shift+←)')}">−10</button>
          <button class="btn" data-a="-1" ${nf} title="${ta('1 frame back (←)')}">−1</button>
          <button class="btn pplay" data-a="play" ${nf} title="${ta('Play / pause (Space, or click the picture)')}">▶</button>
          <button class="btn" data-a="1" ${nf} title="${ta('1 frame on (→)')}">+1</button>
          <button class="btn" data-a="10" ${nf} title="${ta('10 frames on (Shift+→)')}">+10</button></div>
        <div class="pbr">
          <span class="prates" title="${ta('Speed')}"><button class="btn rate" data-r="0.25" ${nf}>¼</button><button class="btn rate" data-r="0.5" ${nf}>½</button><button class="btn rate on" data-r="1" ${nf}>1×</button></span>
          <button class="btn ptog" data-t="loop" ${nf} title="${ta('Repeat - the selected part, else the whole video')}">⟳</button>
          <button class="btn ptog" data-t="mute" ${nf} title="${ta('Sound on / off (M)')}">🔊</button>
          <button class="btn" data-t="full" ${nf} title="${ta('Full screen (F)')}">⛶</button></div></div>
      <div class="pnote small" hidden></div></div>`;
    this.root = $('.player', el); this.v = $('video', el); this.now = $('.now', el); this.pb = $('.pplay', el); this.tot = $('.ptot', el);
    this.src = src; this.note = $('.pnote', el); this.fill = $('.psfill', el); this.head = $('.pshead', el); this.rng = $('.psrange', el);
    this.fl = $('.pflash', el);
    $$('button', this.root).forEach(b => b.addEventListener('mousedown', e => e.preventDefault()));   // keep the focus
    $$('[data-a]', el).forEach(b => b.addEventListener('click', () => {
      const a = b.dataset.a;
      if (a === 'play') this.toggle(); else if (a === 'start') this.seek(0); else this.step(+a);
      this.root.focus({preventScroll: true});
    }));
    $$('[data-r]', el).forEach(b => b.addEventListener('click', () => {
      this.v.playbackRate = +b.dataset.r; $$('[data-r]', el).forEach(x => x.classList.toggle('on', x === b));
    }));
    $$('[data-t]', el).forEach(b => b.addEventListener('click', () => {
      const w = b.dataset.t;
      if (w === 'loop') this.setLoop(!this.looping); else if (w === 'mute') this.mute(); else this.full();
    }));
    this.v.addEventListener('click', () => { const go = this.v.paused; this.toggle(); this.flash(go ? '▶' : '❚❚'); this.root.focus({preventScroll: true}); });
    this.v.addEventListener('dblclick', () => this.full());
    this.v.addEventListener('play', () => { this.pb.textContent = '❚❚'; this.root.classList.add('playing', 'started'); });
    this.v.addEventListener('pause', () => { this.pb.textContent = '▶'; this.root.classList.remove('playing'); });
    this.v.addEventListener('ended', () => { if (this.looping) { this.seek(this._range ? this._range[0] : 0); this.v.play().catch(() => {}); } });
    this.v.addEventListener('loadedmetadata', () => { const T = this.total(); this.tot.textContent = T > 1 ? ` / ${tc(T - 1, this.fps)}` : ''; this.show(); this.paintRange(); });
    this.root.addEventListener('keydown', e => {
      if (e.target.matches('input, textarea, select')) return;
      const k = e.key;
      if (k === ' ') this.toggle();
      else if (k === 'ArrowLeft' || k === 'ArrowRight') this.step((k === 'ArrowRight' ? 1 : -1) * (e.shiftKey ? 10 : 1));
      else if (k === 'Home') this.seek(0);
      else if (k === 'End') { this.v.pause(); this.seek(this.total() - 1); }
      else if (k === 'm' || k === 'M') this.mute();
      else if (k === 'f' || k === 'F') this.full();
      else return;                                          // other keys go on to the page (the analysis page's J K N 1 2 3)
      e.preventDefault(); e.stopPropagation();
    });
    // the seek bar: a click or a drag moves to that frame (the video waits while dragging), the pointer shows where
    const sc = $('.pscrub', el), tip = $('.pstip', el);
    const fAt = e => { const r = sc.getBoundingClientRect(), T = this.total();
      return clamp(Math.round((e.clientX - r.left) / Math.max(1, r.width) * (T - 1)), 0, T - 1); };
    let drag = false, was = false;
    sc.addEventListener('pointerdown', e => {
      if (e.button) return;
      drag = true; was = !this.v.paused; this.v.pause(); sc.setPointerCapture(e.pointerId); sc.classList.add('drag');
      this.seek(fAt(e)); this.root.focus({preventScroll: true});
    });
    sc.addEventListener('pointermove', e => {
      const f = fAt(e), r = sc.getBoundingClientRect();
      tip.hidden = false; tip.style.left = `${clamp(e.clientX - r.left, 46, r.width - 46)}px`;
      tip.innerHTML = `f${f}<span class="tc">${tc(f, this.fps)}</span>`;
      if (drag) this.seekSoon(f);
    });
    const end = () => { if (!drag) return; drag = false; sc.classList.remove('drag'); if (was) this.v.play().catch(() => {}); };
    sc.addEventListener('pointerup', end); sc.addEventListener('pointercancel', end);
    sc.addEventListener('pointerleave', () => { if (!drag) tip.hidden = true; });
    const applyPending = () => {                            // a seek asked for before the video was ready
      if (this.pending == null) return;
      this.v.currentTime = (this.pending + 0.5) / this.fps;
      if (this.v.readyState >= 2) this.pending = null;      // keep it until a frame can really be shown
    };
    this.v.addEventListener('loadedmetadata', applyPending);
    this.v.addEventListener('canplay', applyPending);
    const cb = (now, md) => {
      const f = Math.round(md.mediaTime * this.fps);
      if (f !== this.frame) { this.frame = f; this.show(); this.emit(); }
      if (this._range && this.looping && !this.v.paused && f >= this._range[1]) this.seek(this._range[0]);
      this.vfc = this.v.requestVideoFrameCallback(cb);
    };
    if ('requestVideoFrameCallback' in HTMLVideoElement.prototype) this.vfc = this.v.requestVideoFrameCallback(cb);
    else this.v.addEventListener('timeupdate', () => { this.frame = Math.floor(this.v.currentTime * this.fps + 1e-3); this.show(); this.emit(); });
    // 0.4.2.1: a format this browser cannot play -> a copy for the player only (the codec check, the error event,
    // a video that loads without a picture)
    this.v.addEventListener('error', () => this.needCopy());
    this.v.addEventListener('loadedmetadata', () => { if (!this.v.videoWidth && !this.copied) this.needCopy(); });
    this.checkCodec();
    onCleanup(() => { this.gone = true; this.v.pause(); this.v.removeAttribute('src'); this.v.load(); });
  }
  say(html, cls = '') { this.note.className = 'pnote small ' + cls; this.note.innerHTML = html; this.note.hidden = !html; }
  async checkCodec() {
    let c;
    try { c = await api('/api/player?path=' + encodeURIComponent(this.src)); } catch (e) { return; }
    if (this.gone) return;
    const cannot = FORCE_COPY || (c.codec && !browserPlays(c));
    if (c.copy && cannot) this.useCopy(c.copy, c);
    else if (cannot) this.needCopy(c);
  }
  async needCopy(c = null) {                           // make (or wait for) the copy, then switch to it
    if (this.copying || this.copied || this.gone) return;
    this.copying = true;
    let r;
    try { r = await api('/api/player/copy', {path: this.src}); }
    catch (e) { this.say(t('This video does not play on this PC, and a playable copy could not be started: {err}', {err: esc(e.message)}), 'bad'); return; }
    if (r.copy) { this.useCopy(r.copy, r); return; }
    const fmt = codecWord(r.codec || (c || {}).codec);
    this.say(fmt ? t('<b>This video\'s format ({fmt}) does not play on this PC.</b> MotionLab is making a copy that does, for this player only - the frame numbers stay the same. <a href="#/jobs/{job}">progress</a>', {fmt: esc(fmt), job: r.job})
      : t('<b>This video\'s format does not play on this PC.</b> MotionLab is making a copy that does, for this player only - the frame numbers stay the same. <a href="#/jobs/{job}">progress</a>', {job: r.job}), 'amber');
    const tick = async () => {
      if (this.gone) return;
      let j; try { j = await api(`/api/jobs/${r.job}?since=999999`); } catch (e) { setTimeout(tick, 2000); return; }
      if (['running', 'queued', 'cancelling'].includes(j.status)) { setTimeout(tick, 1000); return; }
      if (j.status !== 'done') { this.say(`${t('The copy for the player could not be made.')} ${reportBtn(j.id)}`, 'bad'); this.copying = false; return; }
      try { const i = await api('/api/player?path=' + encodeURIComponent(this.src)); if (i.copy) this.useCopy(i.copy, i); } catch (e) { /* stays */ }
    };
    tick();
  }
  useCopy(rel, c) {
    this.copied = true; this.copying = false;
    const f = this.frame;                              // the same frame in the copy, once it has loaded
    this.pending = null;
    this.v.addEventListener('loadeddata', () => { if (f) this.v.currentTime = (f + 0.5) / this.fps; }, {once: true});
    this.v.src = fileUrl(rel);
    const fmt = codecWord(c && c.codec);
    this.say(fmt ? t('Playing a copy made for this PC (the original is {fmt}, which does not play here): same frames, same timing. The analysis uses the original.', {fmt: esc(fmt)})
      : t('Playing a copy made for this PC: same frames, same timing. The analysis uses the original.'), 'dim');
  }
  on(fn) { this.fns.push(fn); }
  emit() { this.fns.forEach(f => f(this.frame)); }
  show() {
    this.now.innerHTML = `f${this.frame}<span class="tc">${tc(this.frame, this.fps)}</span>`;
    const T = this.total(), p = T > 1 ? `${clamp(this.frame / (T - 1), 0, 1) * 100}%` : '0%';
    this.fill.style.width = p; this.head.style.left = p;
  }
  total() { return this.N < 1e9 ? this.N : Math.max(1, Math.round((this.v.duration || 0) * this.fps)); }   // frames
  get range() { return this._range; }
  set range(r) { this._range = r; this.paintRange(); }
  paintRange() {                                         // the selected part (an effect) marked on the seek bar
    const r = this._range, T = this.total();
    this.rng.hidden = !r || T < 2;
    if (!this.rng.hidden) { this.rng.style.left = `${r[0] / (T - 1) * 100}%`; this.rng.style.width = `${Math.max(0.4, (r[1] - r[0]) / (T - 1) * 100)}%`; }
  }
  setLoop(on) { this.looping = !!on; $('[data-t=loop]', this.root).classList.toggle('on', this.looping); }
  mute() { this.v.muted = !this.v.muted; const b = $('[data-t=mute]', this.root); b.textContent = this.v.muted ? '🔇' : '🔊'; b.classList.toggle('on', this.v.muted); }
  full() { if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); else this.root.requestFullscreen().catch(() => {}); }
  flash(s) { const f = this.fl; f.textContent = s; f.classList.remove('go'); void f.offsetWidth; f.classList.add('go'); }
  seekSoon(f) {                                          // while dragging: one seek per screen frame
    this.want = f;
    if (!this.raf) this.raf = requestAnimationFrame(() => { this.raf = 0; this.seek(this.want); });
  }
  seek(f) {
    const T = this.total();                              // not loaded yet and no frame count: any frame waits for it
    f = clamp(Math.round(f), 0, (T > 1 ? T : this.N) - 1);
    if (this.v.readyState < 1) this.pending = f;        // not loaded yet: seek on loadedmetadata
    else this.v.currentTime = (f + 0.5) / this.fps;     // middle of frame f: the decoder shows exactly f
    if (f !== this.frame) { this.frame = f; this.show(); this.emit(); }
  }
  step(d) { this.v.pause(); this.seek(this.frame + d); }
  toggle() { if (this.v.paused) this.v.play().catch(() => {}); else this.v.pause(); }
  playRange(a, b) { this.range = [a, b]; this.seek(a); this.v.play().catch(() => {}); }   // range: the setter marks it
}

// ---- the analysis page's Content tab (0.3.5): what the video says (transcript, clickable frame + timecode) and how it
// performs (views against the channel's followers). tools\content.py writes both; they stay on this PC.
function contentTab(el, R, P) {
  el.dataset.done = '1';
  const C = R.content || {}, T = C.transcript, S = C.stats, fps = R.video.fps;
  const n = v => v == null ? '–' : numLoc(Number(v));
  const big = (v, l, hint = '') => `<div class="stat" title="${esc(hint)}"><div class="n">${v}</div><div class="l">${esc(l)}</div></div>`;
  const lang = esc(T && T.lang || '?');
  const kindW = !T ? '' : T.kind === 'auto'
    ? (T.word_timings ? t("the platform's automatic captions ({lang}), timed per word", {lang}) : t("the platform's automatic captions ({lang})", {lang}))
    : (T.word_timings ? t('uploaded subtitles ({lang}), timed per word', {lang}) : t('uploaded subtitles ({lang})', {lang}));
  el.innerHTML = `<div class="grid g2 cgrid"><div class="panel"><div class="row sp"><h2>${t('How it performs')}</h2>
      <button class="btn sm" data-cjob="content_stats">${S ? t('Update the numbers') : t('Get the numbers')}</button></div>
      ${S ? `<div class="row stats">${big(n(S.views), t('views'))}${big(S.outperformer != null ? numStr(S.outperformer) + '×' : '–', t('views ÷ followers'), t("the outperformer score: views against the channel's followers (above 1 = it reached beyond the channel)"))}
          ${big(n(S.views_per_day), t('views a day'), S.days_online ? t('over {n} days online', {n: S.days_online}) : '')}${big(n(S.likes), t('likes'))}${big(n(S.comments), t('comments'))}${big(n(S.followers), t('followers'))}</div>
        <div class="small muted" style="margin-top:8px">${esc(S.uploader || '')} · ${esc(S.platform || '')} · ${t('online since {date}', {date: esc(S.upload_date || '?')})} · ${t('numbers from {when}', {when: esc(S.fetched)})}${(S.history || []).length > 1 ? ` · ${t('{n} fetches kept', {n: S.history.length})}` : ''}</div>`
        : `<div class="muted small">${t("Not fetched yet: one quick request to the video's page (no download).")}</div>`}
      <pre class="log" hidden></pre></div>
    <div class="panel"><h2>${t('Coming soon')}</h2><div class="small muted">${t('The topics, the hook and the call to action, every shot described, the text on screen, and what ~10 videos on one subject have in common.')}</div></div></div>
    <div class="panel" style="margin-top:14px"><div class="row sp"><h2>${t('What it says')}</h2>
      <div class="row">${T ? `<input type="search" id="cq" placeholder="${ta('Search the words…')}" style="width:240px">` : ''}
        <button class="btn sm" data-cjob="content_transcript">${T ? t('Fetch again') : t('Get the transcript')}</button></div></div>
      ${T ? `<div class="small muted" style="margin-bottom:8px">${plural(T.lines.length, 'line')} · ${plural(T.words || 0, 'word')} · ${kindW} · ${t('fetched {when}', {when: esc(T.fetched || '')})} · ${t('click a line to see it in the player')}</div>
        <div class="tlines"><table class="t click"><tbody id="clines">${T.lines.map((l, i) => `<tr data-i="${i}" data-f="${l.start}"><td class="fr">f${l.start}</td><td class="tc">${tc(l.start, fps)}</td><td>${esc(l.text)}</td></tr>`).join('')}</tbody></table></div>`
        : `<div class="muted small">${t("No transcript yet: the platform's own subtitles are fetched in a few seconds, nothing is downloaded. Videos without subtitles cannot be read yet.")}</div>`}
      <pre class="log" hidden></pre></div>`;
  $$('[data-cjob]', el).forEach(b => b.onclick = async () => {
    const pre = b.closest('.panel').querySelector('pre.log');
    const j = await startJob(b.dataset.cjob, {name: R.name, again: !!T}, false);
    if (!j) return;
    b.disabled = true; pre.hidden = false; pre.textContent = '';
    followJob(j.id, pre, jj => {
      toast(`${jj.title}: ${t(jj.status)}`, jj.status === 'done' ? 'ok' : 'err');
      if (jj.status === 'done') api('/api/reference/' + encodeURIComponent(R.name)).then(NR => { R.content = NR.content; contentTab(el, R, P); });
      else b.disabled = false;
    });
  });
  if (!T) return;
  const rows = $$('#clines tr', el);
  rows.forEach(tr => tr.onclick = () => { if (P) { P.v.pause(); P.seek(+tr.dataset.f); $('#player').scrollIntoView({behavior: 'smooth', block: 'center'}); } });
  const q = $('#cq', el);
  q.oninput = () => { const s = q.value.toLowerCase(); rows.forEach((tr, i) => { tr.hidden = !!s && !T.lines[i].text.toLowerCase().includes(s); }); };
  let last = -1;
  if (P) P.on(f => {                                        // the line being said is marked while the video plays
    let k = -1;
    for (let i = 0; i < T.lines.length && T.lines[i].start <= f; i++) if (f <= T.lines[i].end) k = i;
    if (k === last) return;
    if (last >= 0 && rows[last]) rows[last].classList.remove('sel');
    if (k >= 0 && rows[k]) rows[k].classList.add('sel');
    last = k;
  });
}

// ---- one analysis > Overview (0.4): the rhythm, the content side (hook, talking, text) and / or the cinematic side
// (signature effects, transitions, camera, speed, colour) for the video's focus, Claude's breakdown, and Use it
const BD = [['hook', t('The hook (first 3 s)')], ['structure', t('Structure')], ['captions', t('Captions')], ['text_graphics', t('Text & graphics')],
  ['broll', t('B-roll')], ['sound', t('Sound')], ['cta', t('Call to action')], ['transitions', t('Transitions')], ['camera', t('Camera')],
  ['grade', t('Colour grade')], ['rhythm', t('Rhythm')], ['rebuild_tips', t('To make one like it')]];
const kvRow = (k, v) => v == null || v === '' ? '' : `<b>${esc(k)}</b><span>${v}</span>`;
function overviewTab(el, R, showTab) {
  el.dataset.done = '1';
  const PF = R.profile || {}, P = PF.pacing || R.pacing || {}, C = PF.content || {}, K = PF.cinematic || {}, B = R.breakdown || {};
  const f = R.focus || 'both', showC = f !== 'cinematic', showK = f !== 'content';
  const H = C.hook || {}, SP = C.speech, TX = C.text, n = (o, w) => plural(o || 0, w);
  const listOf = o => Object.entries(o || {}).map(([k, v]) => `<span class="chip">${esc(t(k))} <b>${v}</b></span>`).join(' ') || `<span class="dim">${t('none|list')}</span>`;
  const bdVal = v => Array.isArray(v) ? `<ul>${v.map(x => `<li>${linkify(x)}</li>`).join('')}</ul>` : `<div>${linkify(v)}</div>`;
  const reviewed = R.flow && R.flow.done.includes('claude');
  el.innerHTML = `<div class="ovgrid">
    <div class="panel"><h2>${t('Rhythm')}</h2><div class="kv">
      ${kvRow(t('Cuts'), P.cuts_per_min != null ? t('<b>{n}</b> per minute', {n: numStr(P.cuts_per_min)}) : '')}
      ${kvRow(t('Shots'), P.avg_shot_s != null ? t('{avg} s on average (median {median} s · shortest 10 % under {p10} s · longest 10 % over {p90} s)',
        {avg: numStr(P.avg_shot_s), median: numStr(P.median_shot_s ?? '–'), p10: numStr(P.p10_shot_s ?? '–'), p90: numStr(P.p90_shot_s ?? '–')}) : '')}
      ${kvRow(t('First 3 s'), `${n(P.hook_cuts_3s, 'cut')}${P.first_cut_s != null ? ` · ${t('first cut at {s} s', {s: numStr(P.first_cut_s)})}` : ''}`)}
      ${kvRow(t('On the beat'), P.cuts_on_beat_pct != null ? `${t('{pct} % of the plain cuts', {pct: numStr(P.cuts_on_beat_pct)})}${R.audio.bpm ? ` · ${dec(R.audio.bpm, 1)} BPM` : ''}` : (R.audio.bpm ? `${dec(R.audio.bpm, 1)} BPM` : ''))}
      ${kvRow(t('Effects'), P.effects_per_min != null ? t('{n} per minute', {n: numStr(P.effects_per_min)}) : '')}</div></div>
    ${showC ? `<div class="panel"><h2>${t('Content creation')}</h2><div class="kv">
      ${kvRow(t('The hook (3 s)'), [n(H.cuts, 'cut'), H.words != null ? tn(H.words, '{n} word spoken', '{n} words spoken') : '', H.text_on_screen ? t('text on screen') : ''].filter(Boolean).join(' · '))}
      ${SP ? kvRow(t('Talking'), `${t('{wpm} words a minute · talking {pct} % of the time · {words}', {wpm: numStr(SP.words_per_min), pct: numStr(SP.talk_pct), words: n(SP.words, 'word')})} <span class="dim">(${esc(SP.source === 'speech' ? t('speech to text') : t("the platform's subtitles"))})</span>`)
        : kvRow(t('Talking'), `<span class="dim">${t('no transcript yet')}</span> <button class="btn sm ghost" data-ovgo="content">${t('What it says →')}</button>`)}
      ${TX ? kvRow(t('Text on screen'), `${TX.appearances ? t('pops up {times} ({per}/min, {each} s each)', {times: n(TX.appearances, 'time'), per: numStr(TX.per_min), each: numStr(TX.avg_on_s ?? '–')}) : t('no text pops up')}${TX.captions_likely ? ` · <b>${t('burned-in captions')}</b>` : ''}${TX.visible_pct != null ? ` <span class="dim">· ${t('text-like shapes {pct} % of the time', {pct: numStr(TX.visible_pct)})}</span>` : ''}`) : ''}
      </div></div>` : ''}
    ${showK ? `<div class="panel"><h2>${t('Cinematic')}</h2><div class="kv">
      ${kvRow(t('Signature'), (K.signature || []).map(chip).join(' ') || `<span class="dim">${t('no effects besides cuts')}</span>`)}
      ${kvRow(t('Transitions'), listOf(K.transitions))}
      ${kvRow(t('Camera'), listOf(K.camera))}
      ${kvRow(t('Speed'), listOf(K.speed))}
      ${PF.colour ? kvRow(t('Colour'), esc(PF.colour.line || '')) : ''}</div></div>` : ''}
  </div>
  ${showK || R.colour ? colourPanel(R) : ''}
  <div class="panel bd"><div class="row sp"><h2>${t('What makes it work')} <span class="small muted">· ${t("Claude's breakdown")}</span></h2>${B.summary ? '' : ''}</div>
    ${Object.keys(B).length ? `${B.summary ? `<p class="bdsum">${linkify(B.summary)}</p>` : ''}<div class="bdgrid">${BD.filter(([k]) => B[k]).map(([k, l]) => `<div class="bdi"><h3>${l}</h3>${bdVal(B[k])}</div>`).join('')}</div>`
      : `<div class="small muted">${reviewed ? t('Claude checked the effects before 0.4 - ask it again for the breakdown:') : t('Claude has not checked this video yet. It looks at every effect and writes what makes the video work:')}</div>
         <div class="row" style="margin-top:8px">${claudeBtn(R.review_prompt, reviewed ? t('Ask Claude for the breakdown') : t('Send to Claude'), 'review', R.title, 'pri')}</div>`}</div>
  <div class="panel useit"><h2>${t('Use it')}</h2><div class="row">
    <button class="btn pri" data-use="edit"><svg class="i"><use href="#i-edit"/></svg>${t('Edit my clips like this…')}</button>
    <button class="btn" data-use="prompts"><svg class="i"><use href="#i-generate"/></svg>${t('Prompts for AI tools like this…')}</button>
    <button class="btn ghost" data-use="again" title="${ta('the same video again with another focus - the measurements are re-used')}">${t('Analyse again with another focus…')}</button></div>
    <div class="small muted" style="margin-top:8px">${t('Claude also reads it from its memory when you edit or generate - nothing to copy.')}</div></div>
  <div id="ovtook"></div>`;
  el.insertAdjacentHTML('afterbegin', `<div class="liveline" data-live="${esc(R.name)}" data-name="${esc(R.label || R.title || R.name)}" hidden></div>`);
  liveLine(LIVE);
  tookPanel($('#ovtook', el), 'analysis', R.name);
  $$('[data-ovgo]', el).forEach(b => b.onclick = () => showTab(b.dataset.ovgo, true));
  wireColour(el, R);
  $('[data-use=edit]', el).onclick = () => newEdit({from: 'reference', pick: R.name});
  $('[data-use=prompts]', el).onclick = () => aiPromptsModal('shot', R.name);
  $('[data-use=again]', el).onclick = () => addVideosModal({files: R.source ? [R.source] : [], focus: f === 'both' ? 'content' : 'both', pick: true, again: true});
}

// ---- the Overview's Colour & look (0.4, the cinematic focus: "colour grading"): colour\colour.json (motionlab.colour)
function colourPanel(R) {
  const C = R.colour;
  if (!C) return `<div class="panel colour"><h2>${esc(t('Colour & look'))}</h2><div class="small muted">${t('Not measured yet - it takes a few seconds (no new decoding).')}</div>
    <div class="row" style="margin-top:8px"><button class="btn sm" id="colgo">${t('Measure the colour')}</button></div></div>`;
  const S = C.summary || {}, N = Math.max(1, (C.shots[C.shots.length - 1] || {}).end + 1 || 1);
  const num = (v, u = '') => v == null ? '–' : `${numStr(Math.round(v * 10) / 10)}${u}`;
  const warm = S.warmth == null ? '–' : S.warmth > 6 ? t('warm ({n})', {n: num(S.warmth)}) : S.warmth < -4 ? t('cool ({n})', {n: num(S.warmth)}) : t('neutral ({n})', {n: num(S.warmth)});
  return `<div class="panel colour"><div class="row sp"><h2>${esc(t('Colour & look'))}</h2><span class="small muted">${esc(t(C.made_from || ''))}</span></div>
    <div class="row" style="gap:6px;margin-bottom:10px">${(S.words || []).map(w => `<span class="chip">${esc(t(w))}</span>`).join('') || '<span class="chip">natural</span>'}${S.consistent === false ? `<span class="small amber">${t('changes from shot to shot')}</span>` : ''}</div>
    ${(S.palette || []).length ? `<div class="cpal">${S.palette.map(([c, w]) => `<div class="cpc" style="flex:${Math.max(0.06, w)};background:${esc(c)}" title="${esc(c)} · ${Math.round(w * 100)} %"><span>${esc(c)}</span></div>`).join('')}</div>` : ''}
    <div class="cstrip" title="${ta("every shot's main colour, in order")}">${C.shots.map(x => `<i style="flex:${x.end - x.start + 1};background:${esc(((x.palette || [])[0] || ['#333'])[0])}" data-f="${x.start}"
      data-tip="${esc(`f${x.start}-${x.end} (${x.tc}-${x.tc_end})${x.words.length ? ': ' + x.words.map(w => t(w)).join(', ') : ''}`)}"></i>`).join('')}</div>
    <div class="kv" style="margin-top:10px">
      ${kvRow(t('Brightness'), t('{level} · blacks {black} · whites {white} · contrast {contrast}', {level: num(S.brightness, ' %'), black: num(S.black, ' %'), white: num(S.white, ' %'), contrast: num(S.contrast)}))}
      ${kvRow(t('Colour'), S.bw ? esc(t('black & white')) : `${t('saturation {sat} · {warmth} · tint {tint}', {sat: num(S.saturation, ' %'), warmth: warm, tint: num(S.tint)})}${S.shadows && S.highlights ? ` · ${t('shadows {shadows}, highlights {highlights}', {shadows: hueWord(S.shadows), highlights: hueWord(S.highlights)})}` : ''}`)}
      ${S.letterbox || (S.vignette != null && S.vignette < 0.85) ? kvRow(t('Frame|framing'), [S.letterbox ? t('letterbox {size}', {size: esc(S.letterbox)}) : '', S.vignette != null && S.vignette < 0.85 ? t('vignette (corners {pct} % of the centre)', {pct: Math.round(S.vignette * 100)}) : ''].filter(Boolean).join(' · ')) : ''}</div>
    <div class="small muted" style="margin-top:8px">${t('An edit <b>in its style</b> matches your footage to this look (a match LUT - also for DaVinci Resolve).')}</div></div>`;
}
function hueWord(ab) {
  const [a, b] = ab, c = Math.hypot(a, b);
  if (c < 3) return t('neutral|hue');
  const h = (Math.atan2(b, a) * 180 / Math.PI + 360) % 360;
  return [[20, t('red|hue')], [50, t('orange|hue')], [75, t('yellow|hue')], [165, t('green|hue')], [200, t('teal|hue')], [260, t('blue|hue')], [300, t('purple|hue')], [345, t('magenta|hue')], [360, t('red|hue')]].find(([l]) => h <= l)[1];
}
function wireColour(el, R) {
  $$('.cstrip i', el).forEach(i => { i.onmousemove = e => showTip(esc(i.dataset.tip), e.clientX, e.clientY); i.onmouseleave = hideTip; });
  const go = $('#colgo', el);
  if (go) go.onclick = async () => {
    try { await api('/api/jobs', {kind: 'colour', args: {name: R.name}, queue: true}); toast(t('Measuring the colour - a few seconds'), 'ok'); setTimeout(route, 4000); }
    catch (e) { toast(e.message, 'err'); }
  };
}

// ============================================================================================ timeline
class Timeline {
  /* events (lanes by overlap), hard cuts, shots, beats, drops; zoom = frames each side of the playhead (0 = all) */
  constructor(wrap, R, opts = {}) {
    this.c = $('canvas', wrap); this.R = R; this.fps = R.video.fps; this.N = R.video.frames; this.zoom = opts.zoom || 0;
    this.opts = opts; this.play = 0; this.sel = null; this.v0 = 0; this.v1 = this.N - 1;
    this.lanes = Timeline.pack(R.events, Math.max(2, this.N / 600));
    this.H = this.c.height;
    this.c.style.height = this.H + 'px';     // fixed now: a draw never resizes it (no ResizeObserver loop when shown later)
    this.c.addEventListener('mousemove', e => this.hover(e));
    this.c.addEventListener('mouseleave', hideTip);
    this.c.addEventListener('click', e => this.click(e));
    const ro = new ResizeObserver(() => this.draw()); ro.observe(this.c); onCleanup(() => ro.disconnect());
  }
  static pack(evs, gap) {
    const ends = [], lane = {};
    [...evs].sort((a, b) => a.start - b.start).forEach(e => {
      let i = ends.findIndex(x => x + gap < e.start);
      if (i < 0) { i = ends.length; ends.push(0); }
      ends[i] = e.end; lane[e.id] = i;
    });
    return {lane, n: Math.max(1, ends.length)};
  }
  setPlay(f) {
    this.play = f;
    if (this.zoom) { this.v0 = f - this.zoom; this.v1 = f + this.zoom; }
    this.draw();
  }
  x(f) { return (f - this.v0) / (this.v1 - this.v0 + 1) * this.W; }
  fAt(x) { return Math.floor(this.v0 + x / this.W * (this.v1 - this.v0 + 1)); }
  laneY(i) { const top = 16, h = (this.H - 34) / this.lanes.n; return [top + i * h, Math.max(4, h - 2)]; }
  draw() {
    const c = this.c, dpr = window.devicePixelRatio || 1, W = c.clientWidth, H = this.H;
    if (!W) return;
    this.W = W; c.width = W * dpr; c.height = H * dpr;
    const g = c.getContext('2d'); g.scale(dpr, dpr); g.clearRect(0, 0, W, H);
    const R = this.R, vis = (a, b) => b >= this.v0 && a <= this.v1, ppf = W / (this.v1 - this.v0 + 1);
    R.shots.forEach((s, i) => { if (vis(s.start, s.end)) { g.fillStyle = i % 2 ? '#141418' : '#101013'; g.fillRect(this.x(s.start), 12, this.x(s.end + 1) - this.x(s.start), H - 30); } });
    g.fillStyle = '#3a3a44';
    R.audio.beats.forEach(b => { if (vis(b, b)) g.fillRect(Math.round(this.x(b)), 0, 1, 5); });
    g.fillStyle = '#6a6a78';
    R.audio.downbeats.forEach(b => { if (vis(b, b)) g.fillRect(Math.round(this.x(b)), 0, 1, 9); });
    R.events.forEach(e => {
      if (!vis(e.start, e.end)) return;
      const [y, h] = this.laneY(this.lanes.lane[e.id]);
      const x0 = this.x(e.start), w = Math.max(2, this.x(e.end + 1) - x0);
      g.fillStyle = FAM[e.family] || '#888'; g.globalAlpha = e.false_alarm ? 0.35 : 0.9; g.fillRect(x0, y, w, h); g.globalAlpha = 1;
      const v = (this.opts.verdict || (() => ''))(e.id);
      if (v) { g.fillStyle = VCOL[v]; g.fillRect(x0, y + h - 3, w, 3); }
      if (this.sel === e.id) { g.strokeStyle = '#fff'; g.lineWidth = 2; g.strokeRect(x0 - 1, y - 1, w + 2, h + 2); }
      if (this.zoom && w > 34) { g.fillStyle = '#000'; g.font = '11px Consolas'; g.fillText(e.id, x0 + 3, y + h - 4); }
    });
    g.fillStyle = '#e9e9ec';
    R.cuts.forEach(cu => { if (vis(cu.frame, cu.frame)) g.fillRect(Math.round(this.x(cu.frame)), 12, 1, H - 30); });
    // possible misses: a red dashed line + a red ▲ (red until you answered it)
    (R.near_misses || []).forEach(m => {
      if (!vis(m.frame, m.frame)) return;
      const x = Math.round(this.x(m.frame) + (this.zoom ? ppf / 2 : 0)), open = !(this.opts.missDone || (() => false))(m.frame);
      g.fillStyle = open ? '#ff3b3b' : '#8a4b4b';
      for (let y = 12; y < H - 24; y += 6) g.fillRect(x, y, 1, 3);
      g.beginPath(); g.moveTo(x - 6, H - 17); g.lineTo(x + 6, H - 17); g.lineTo(x, H - 27); g.fill();
    });
    g.fillStyle = '#ffc400';
    R.audio.drops.forEach(d => { if (!vis(d.frame, d.frame)) return; const x = this.x(d.frame); g.beginPath(); g.moveTo(x - 5, 0); g.lineTo(x + 5, 0); g.lineTo(x, 8); g.fill(); });
    // time ruler
    g.fillStyle = '#5c5c66'; g.font = '10.5px Consolas';
    const fpsN = Math.max(1, Math.round(this.fps));
    const steps = [1, 5, fpsN, fpsN * 5, fpsN * 10, fpsN * 30, fpsN * 60];
    const lab = steps.find(s => s * ppf >= 70) || fpsN * 60;
    const tick = steps.find(s => s * ppf >= 6) || lab;
    for (let f = Math.ceil(Math.max(0, this.v0) / tick) * tick; f <= Math.min(this.N - 1, this.v1); f += tick) {
      const x = Math.round(this.x(f)), big = f % lab === 0;
      g.fillRect(x, H - 16, 1, big ? 6 : 3);
      if (big) g.fillText(this.zoom ? `f${f}` : tc(f, this.fps).slice(3, 8), x + 2, H - 3);
    }
    // playhead
    const px = Math.round(this.x(this.play) + (this.zoom ? ppf / 2 : 0));
    g.fillStyle = '#ff5a5a'; g.fillRect(px, 0, 2, H);
    if (this.zoom) {
      const lbl = `f${this.play}  ${tc(this.play, this.fps)}`; g.font = 'bold 11px Consolas';
      const tw = g.measureText(lbl).width + 10, lx = Math.min(px + 4, W - tw - 2);
      g.fillStyle = '#ff5a5a'; g.fillRect(lx, H - 15, tw, 14); g.fillStyle = '#000'; g.fillText(lbl, lx + 5, H - 4);
    }
  }
  hit(e) {
    const r = this.c.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, f = this.fAt(x);
    const slack = Math.max(1, Math.round(3 / (this.W / (this.v1 - this.v0 + 1))));
    const miss = y >= this.H - 30 && y <= this.H - 14 ? (this.R.near_misses || []).find(m => Math.abs(this.x(m.frame) - x) <= 7) : null;
    const ev = miss ? null : this.R.events.find(ev => { const [ly, h] = this.laneY(this.lanes.lane[ev.id]); return y >= ly && y <= ly + h && f >= ev.start - slack && f <= ev.end + slack; });
    return {f: clamp(f, 0, this.N - 1), ev, miss};
  }
  hover(e) {
    const {f, ev, miss} = this.hit(e);
    if (miss) showTip(`<b class="bad">${t('Possible miss')}</b> ${ftc(miss.frame, this.fps)}<br>${esc(miss.why)}<br><span class="dim">${t('click to check it')}</span>`, e.clientX, e.clientY);
    else if (ev) showTip(`<b class="amber mono">${ev.id}</b> ${esc(t(ev.label ?? ''))}<br>${frange(ev.start, ev.end, this.fps)}`, e.clientX, e.clientY);
    else showTip(t('{at} · click to jump', {at: ftc(f, this.fps)}), e.clientX, e.clientY);
  }
  click(e) {
    const {f, ev, miss} = this.hit(e);
    if (miss && this.opts.onMiss) this.opts.onMiss(miss);
    else if (ev && this.opts.onSelect) this.opts.onSelect(ev); else if (this.opts.onSeek) this.opts.onSeek(f);
  }
}
