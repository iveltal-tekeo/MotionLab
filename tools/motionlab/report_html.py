"""report.html renderer. Static HTML (readable without JS) + a small script for verdicts and feedback text.

Its words follow the app's language (Settings > Language, 2026-10-19): in a job MOTIONLAB_LANG gives it (jobs.py starts
every tool with the app's), from the command line it is English (motionlab.i18n.lang). What it shows from the analysis
(Claude's review, the measured evidence, ids, frame numbers, timecodes), the data it embeds and the MOTIONLAB FEEDBACK
text its button writes (tools\\feedback.py reads it) stay as they are."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from . import i18n as I18N
from . import taxonomy
from .styles import label as style_label

E = html.escape

CSS = r"""
:root{color-scheme:dark;--bg:#0d0d0d;--surface:#1a1a19;--surface2:#232321;--line:#2c2c2a;--ink:#f4f4f1;
--ink2:#c3c2b7;--muted:#898781;--accent:#ffc400;--good:#0ca30c;--warn:#fab219;--bad:#d03b3b;--info:#3987e5;
--chip:#2b2b28;--code:#141413}
@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){color-scheme:light;--bg:#f9f9f7;--surface:#fcfcfb;
--surface2:#f1f0ec;--line:#e1e0d9;--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6d68;--accent:#a86f00;--chip:#eceae4;
--code:#f4f3ef}}
:root[data-theme="light"]{color-scheme:light;--bg:#f9f9f7;--surface:#fcfcfb;--surface2:#f1f0ec;--line:#e1e0d9;
--ink:#0b0b0b;--ink2:#52514e;--muted:#6f6d68;--accent:#a86f00;--chip:#eceae4;--code:#f4f3ef}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--info)}
.mono,.tc,td.num{font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;font-variant-numeric:tabular-nums}
header.top{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);
backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.topin{max-width:1500px;margin:0 auto;padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.topin .title{font-weight:650;font-size:16px;margin-right:auto;overflow-wrap:anywhere}
.topin nav a{color:var(--ink2);text-decoration:none;margin-right:12px;font-size:14px}
.topin nav a:hover{color:var(--ink)}
.progress{font-size:13px;color:var(--ink2)}
.btn{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface2);color:var(--ink);
border-radius:8px;padding:5px 10px;cursor:pointer}
.btn:hover{border-color:var(--muted)}
main{max-width:1500px;margin:0 auto;padding:16px}
section.block{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:0 0 18px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:18px;margin:0 0 12px}h3{font-size:15px;margin:14px 0 6px;color:var(--ink2)}
.sub{color:var(--ink2);font-size:14px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
dl.kv{display:grid;grid-template-columns:max-content 1fr;gap:3px 14px;margin:0;font-size:14px}
dl.kv dt{color:var(--muted)}dl.kv dd{margin:0;overflow-wrap:anywhere}
.counts{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px 18px;font-size:14px}
.counts div{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:3px 0}
.counts b{font-variant-numeric:tabular-nums}
.note{font-size:13px;color:var(--muted);margin:8px 0 0}
.overview{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:#fcfcfb}
.overview img{display:block;max-width:none;height:auto}
.overview.fit img{max-width:100%}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:middle}
th{color:var(--muted);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.03em;background:var(--surface)}
tr:hover td{background:var(--surface2)}
.tablewrap{overflow-x:auto}
.chip{display:inline-block;padding:1px 8px;border-radius:999px;background:var(--chip);font-size:12.5px;white-space:nowrap}
.chip.yes{background:color-mix(in srgb,var(--good) 25%,var(--chip))}
.chip.drop{background:color-mix(in srgb,var(--bad) 30%,var(--chip))}
.chip.high{background:color-mix(in srgb,var(--good) 22%,var(--chip))}
.chip.medium{background:color-mix(in srgb,var(--warn) 25%,var(--chip))}
.chip.low{background:color-mix(in srgb,var(--bad) 22%,var(--chip))}
.chip.draft{background:color-mix(in srgb,var(--info) 25%,var(--chip))}
.vstat{font-size:12.5px;white-space:nowrap}
.vstat.correct{color:var(--good)}.vstat.partly{color:var(--warn)}.vstat.wrong{color:var(--bad)}
article.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;margin:0 0 22px;overflow:hidden;scroll-margin-top:64px}
.cardhead{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:baseline;padding:14px 18px;border-bottom:1px solid var(--line)}
.cardhead .id{font-weight:700;font-size:18px}
.cardhead .ty{font-weight:650;font-size:18px}
.cardhead .rng{color:var(--ink2)}
.cardbody{display:grid;grid-template-columns:minmax(300px,520px) 1fr;gap:18px;padding:16px 18px}
@media (max-width:900px){.cardbody{grid-template-columns:1fr}}
video{width:100%;border-radius:8px;background:#000;display:block}
.speed{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--muted)}
.speed .btn{padding:2px 8px}
.speed .btn.on{border-color:var(--accent);color:var(--accent)}
.desc p{margin:0 0 8px}
.desc ul{margin:0 0 6px;padding-left:18px}
.desc li{margin:2px 0}
.rebuild{background:var(--code);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:14px}
.sheets{padding:0 18px 12px}
.sheets img{width:100%;height:auto;display:block;border-radius:8px;margin:0 0 10px;border:1px solid var(--line)}
.verdict{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start;padding:12px 18px 16px;border-top:1px solid var(--line);background:var(--surface2)}
.vbtns{display:flex;gap:6px}
.vbtn{font:inherit;font-size:14px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:8px;
padding:6px 12px;cursor:pointer;min-height:36px}
.vbtn[data-v=correct].on{background:var(--good);border-color:var(--good);color:#fff}
.vbtn[data-v=partly].on{background:var(--warn);border-color:var(--warn);color:#111}
.vbtn[data-v=wrong].on{background:var(--bad);border-color:var(--bad);color:#fff}
textarea{font:inherit;font-size:14px;width:100%;background:var(--surface);color:var(--ink);border:1px solid var(--line);
border-radius:8px;padding:8px}
.verdict textarea{flex:1;min-width:260px;min-height:38px;height:38px;resize:vertical}
.cutthumb{height:40px;border-radius:4px;display:block}
.cutv{display:flex;gap:4px}
.cutv .vbtn{padding:2px 8px;min-height:28px;font-size:12.5px}
.cutnote{min-width:160px;height:30px;min-height:30px;padding:4px 6px;font-size:13px}
#fbout{min-height:240px;font-family:ui-monospace,Consolas,monospace;font-size:13px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:10px 0}
.reviewed{font-size:12.5px;color:var(--muted)}
tbody tr:nth-child(even) td{background:color-mix(in srgb,var(--surface2) 70%,var(--surface))}
table tbody tr:hover td{background:color-mix(in srgb,var(--accent) 10%,var(--surface2))}
tbody tr.fa td{color:var(--muted)}
article.card.alt{background:color-mix(in srgb,var(--surface2) 55%,var(--surface))}
article.card{border-left:4px solid var(--line)}
article.card .cardhead{background:color-mix(in srgb,var(--surface2) 85%,transparent)}
article.card.fa{border-left-color:var(--muted);opacity:.92}
.fareason{flex-basis:100%;color:var(--muted);font-size:13.5px}
details.fold{margin:0 18px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface)}
article.card.alt details.fold{background:var(--surface2)}
details.fold>summary{cursor:pointer;padding:8px 12px;color:var(--ink2);font-size:14px;list-style:none;user-select:none}
details.fold>summary::-webkit-details-marker{display:none}
details.fold>summary::before{content:"\25B8  ";color:var(--accent)}
details.fold[open]>summary::before{content:"\25BE  "}
details.fold>.in{padding:2px 14px 12px}
details.fold .sheets{padding:6px 0 0}
details.facard{margin:0 18px 14px}
.nm{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:12px}
.nmi{border:1px solid var(--line);border-radius:10px;padding:10px;background:var(--surface2)}
.nmi .fr3{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}
.nmi .fr3 img{width:100%;border-radius:4px;display:block}
.nmi .fr3 span{font-size:11.5px;color:var(--muted)}
.nmi .row input{flex:1;min-width:120px;font:inherit;font-size:13px;padding:4px 8px;border-radius:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink)}
.nmi.added{border-color:var(--warn)}
"""

JS = r"""
(function(){
const DATA = JSON.parse(document.getElementById('ml-data').textContent);
// the page's words in the reader's language: the renderer writes them into ml-words outside English
let W = {};
try { W = JSON.parse(document.getElementById('ml-words').textContent) || {}; } catch(e) {}
function t(en, vars){ const s = typeof W[en] === 'string' ? W[en] : en;
  return vars ? s.replace(/\{(\w+)\}/g, (m, k) => k in vars ? String(vars[k]) : m) : s; }
// verdicts live in this browser under the video's name (stable when the analysis is re-run), start from the
// verdicts saved in the lab (MotionLab app / imported feedback) and pick up ones given on an older run
const KEY = 'motionlab:' + DATA.video;
let S = {events:{}, cuts:{}, missed:''};
try {
  let raw = localStorage.getItem(KEY);
  if (!raw) {
    const old = Object.keys(localStorage).filter(k => k.startsWith('motionlab:' + DATA.video + '-')).sort().pop();
    if (old) raw = localStorage.getItem(old);
  }
  const mine = raw ? JSON.parse(raw) : {}, saved = DATA.saved || {};
  S = {events: Object.assign({}, saved.events || {}, mine.events || {}),
       cuts: Object.assign({}, saved.cuts || {}, mine.cuts || {}),
       missed: mine.missed || saved.missed || ''};
} catch(e) {}
function save(){ try { localStorage.setItem(KEY, JSON.stringify(S)); } catch(e) {} }
const theme = document.getElementById('theme');
const THEME = {auto: t('Theme: auto'), dark: t('Theme: dark'), light: t('Theme: light')};
function applyTheme(mode){ if (mode==='auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', mode);
  theme.textContent = typeof THEME[mode] === 'string' ? THEME[mode] : t('Theme: {mode}', {mode}); }
let th = 'auto'; try { th = localStorage.getItem('motionlab:theme') || 'auto'; } catch(e) {}
applyTheme(th);
theme.addEventListener('click', () => { th = th==='auto' ? 'dark' : th==='dark' ? 'light' : 'auto';
  applyTheme(th); try { localStorage.setItem('motionlab:theme', th); } catch(e) {} });

const VWORD = {correct: t('Correct'), partly: t('Partly'), wrong: t('Wrong')};
function paint(){
  let n = 0;
  DATA.events.forEach(ev => {
    const st = S.events[ev.id] || {};
    document.querySelectorAll('[data-ev="'+ev.id+'"] .vbtn').forEach(b => b.classList.toggle('on', b.dataset.v === st.v));
    const cell = document.getElementById('st-' + ev.id);
    if (cell) { cell.className = 'vstat ' + (st.v || ''); cell.textContent = st.v ? (VWORD[st.v] || st.v[0].toUpperCase() + st.v.slice(1)) : '—'; }
    if (st.v) n++;
  });
  DATA.cuts.forEach(c => {
    const st = S.cuts[c.id] || {};
    document.querySelectorAll('[data-cut="'+c.id+'"] .vbtn').forEach(b => b.classList.toggle('on', b.dataset.v === st.v));
  });
  const real = DATA.events.filter(ev => !ev.fa), fas = DATA.events.filter(ev => ev.fa);
  const done = list => list.filter(ev => (S.events[ev.id] || {}).v).length;
  const nums = {done: done(real), total: real.length, fdone: done(fas), ftotal: fas.length};
  document.getElementById('prog').textContent = fas.length
    ? t('{done} / {total} effects reviewed · false alarms {fdone} / {ftotal} (optional)', nums)
    : t('{done} / {total} effects reviewed', nums);
}
const agree = document.getElementById('agreefa');
if (agree) agree.addEventListener('click', () => {
  DATA.events.filter(ev => ev.fa).forEach(ev => {
    S.events[ev.id] = S.events[ev.id] || {};
    if (!S.events[ev.id].v) S.events[ev.id].v = 'correct';
  });
  save(); paint();
});
document.querySelectorAll('[data-ev]').forEach(box => {
  const id = box.dataset.ev;
  box.querySelectorAll('.vbtn').forEach(b => b.addEventListener('click', () => {
    S.events[id] = S.events[id] || {};
    S.events[id].v = (S.events[id].v === b.dataset.v) ? '' : b.dataset.v; save(); paint(); }));
  const ta = box.querySelector('textarea');
  ta.value = (S.events[id] || {}).note || '';
  ta.addEventListener('input', () => { S.events[id] = S.events[id] || {}; S.events[id].note = ta.value; save(); });
});
document.querySelectorAll('[data-cut]').forEach(box => {
  const id = box.dataset.cut;
  box.querySelectorAll('.vbtn').forEach(b => b.addEventListener('click', () => {
    S.cuts[id] = S.cuts[id] || {};
    S.cuts[id].v = (S.cuts[id].v === b.dataset.v) ? '' : b.dataset.v; save(); paint(); }));
  const ta = box.querySelector('textarea');
  if (ta) { ta.value = (S.cuts[id] || {}).note || '';
    ta.addEventListener('input', () => { S.cuts[id] = S.cuts[id] || {}; S.cuts[id].note = ta.value; save(); }); }
});
const missed = document.getElementById('missed');
missed.value = S.missed || '';
missed.addEventListener('input', () => { S.missed = missed.value; save(); });

document.querySelectorAll('.speed').forEach(sp => {
  const vid = document.getElementById(sp.dataset.vid);
  sp.querySelectorAll('.btn').forEach(b => b.addEventListener('click', () => {
    vid.playbackRate = parseFloat(b.dataset.rate);
    sp.querySelectorAll('.btn').forEach(x => x.classList.toggle('on', x === b)); vid.play(); }));
});
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver(es => es.forEach(e => {
    const v = e.target; if (e.isIntersecting) { v.play().catch(()=>{}); } else { v.pause(); } }), {threshold: 0.35});
  document.querySelectorAll('video[data-auto]').forEach(v => io.observe(v));
}

function line(ev){ return ev.id + ' | ' + ev.type + ' | f' + ev.start + '-' + ev.end + ' (' + ev.tc_start + ' - ' + ev.tc_end + ')'; }
document.getElementById('gen').addEventListener('click', () => {
  const L = [];
  L.push('MOTIONLAB FEEDBACK v1');
  L.push('video: ' + DATA.video + ' | analysis: ' + DATA.analysis_id + ' | fps: ' + DATA.fps + ' | frames are 0-based');
  L.push('report: ' + DATA.report_path);
  L.push('--- events ---');
  const un = [];
  DATA.events.forEach(ev => {
    const st = S.events[ev.id] || {};
    if (!st.v && !(st.note||'').trim()) { un.push(ev.id); return; }
    let s = (st.v ? st.v.toUpperCase() : 'NOTE') + ' | ' + line(ev);
    if ((st.note||'').trim()) s += ' | note: ' + st.note.trim().replace(/\s*\n\s*/g, ' / ');
    L.push(s);
  });
  if (un.length) L.push('(no verdict: ' + un.join(', ') + ')');
  const cl = [];
  DATA.cuts.forEach(c => { const st = S.cuts[c.id] || {};
    if (st.v || (st.note||'').trim()) cl.push((st.v ? st.v.toUpperCase() : 'NOTE') + ' | ' + c.id + ' | hard cut | f' + c.frame + ' (' + c.tc + ')' + ((st.note||'').trim() ? ' | note: ' + st.note.trim().replace(/\s*\n\s*/g,' / ') : '')); });
  L.push('--- hard cuts ---');
  if (cl.length) cl.forEach(x => L.push(x)); else L.push('(all hard cuts accepted / not reviewed)');
  L.push('--- missed effects / general notes ---');
  L.push((S.missed||'').trim() || '(none)');
  L.push('END');
  const out = document.getElementById('fbout'); out.value = L.join('\n'); out.focus(); out.select();
});
document.getElementById('copy').addEventListener('click', async () => {
  const out = document.getElementById('fbout'); const msg = document.getElementById('copymsg');
  if (!out.value) document.getElementById('gen').click();
  try { await navigator.clipboard.writeText(out.value); msg.textContent = t('Copied - paste it into Claude.'); }
  catch(e) { out.select(); try { document.execCommand('copy'); msg.textContent = t('Copied - paste it into Claude.'); }
    catch(e2) { msg.textContent = t('Select the text and press Ctrl+C.'); } }
});
document.getElementById('reset').addEventListener('click', () => {
  if (!confirm(t('Clear all verdicts and notes for this report?'))) return;
  S = {events:{}, cuts:{}, missed:''}; save(); location.reload(); });
document.querySelectorAll('.nmi').forEach(box => {
  const b = box.querySelector('button'), inp = box.querySelector('input');
  b.addEventListener('click', () => {
    const line = 'missed: ' + box.dataset.where + (inp.value.trim() ? ' - ' + inp.value.trim() : '');
    S.missed = ((S.missed || '').trim() + '\n' + line).trim(); save();
    const ta = document.getElementById('missed'); if (ta) ta.value = S.missed;
    box.classList.add('added'); b.textContent = t('Added to missed effects');
  });
});
paint();
})();
"""


def _chip(text, cls=""):
    return f'<span class="chip {cls}">{E(str(text))}</span>'


def _th(*heads) -> str:
    return "".join(f"<th>{h}</th>" for h in heads)


def _n(x, spec: str, lg: str) -> str:
    """A measured number as the reader's language writes it: format(x, spec); Spanish with a decimal comma (and
    12.345,6 from five digits on, like motionlab.i18n.num). Never for frame numbers, fps, timecodes or bar.beat."""
    s = format(x, spec)
    if lg == "en":
        return s
    sign = s[:1] if s[:1] in "+-" else ""
    whole, _, frac = s[len(sign):].partition(".")
    if whole.isdigit() and len(whole) > 4:
        whole = f"{int(whole):,}".replace(",", ".")
    return sign + whole + ("," + frac if frac else "")


def _conf(c) -> str:
    """An effect's confidence (the lab's high / medium / low, also its chip's CSS class) in the reader's words."""
    return {"high": I18N.t("high|confidence"), "medium": I18N.t("medium|confidence"),
            "low": I18N.t("low|confidence")}.get(c, c)


def _origin(o) -> str:
    """Where an effect comes from (the lab's post / camera / unclear; a review may write its own words: kept)."""
    return {"post": I18N.t("post|origin"), "camera": I18N.t("camera|origin"),
            "unclear": I18N.t("unclear|origin")}.get(o, o)


def _kind(k) -> str:
    """A plain cut's kind (assemble.cut_rows: hard cut / jump cut)."""
    return {"hard cut": I18N.t("hard cut"), "jump cut": I18N.t("jump cut")}.get(k, k)


JS_KEY = re.compile(r"\bt\('((?:[^'\\]|\\.)*)'")


def _js_words(lg: str) -> str:
    """The page script's words (its t('...') keys) in the reader's language, as the JSON element the script reads;
    nothing in English (the script's own words)."""
    if lg == "en":
        return ""
    w = {k: I18N.t(k) for k in dict.fromkeys(JS_KEY.findall(JS))}
    w = {k: v for k, v in w.items() if v != k}
    return ("<script type='application/json' id='ml-words'>" + json.dumps(w, ensure_ascii=False).replace("</", "<\\/")
            + "</script>") if w else ""


def _saved_verdicts(p: Path) -> dict:
    """The verdicts saved in the lab (MotionLab app, imported feedback) - the page starts from these."""
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        return {"events": v.get("events", {}), "cuts": v.get("cuts", {}), "missed": v.get("missed", "")}
    except (OSError, ValueError):
        return {}


def render(d: dict, out: Path) -> None:
    v = d["video"]
    a = d.get("audio") or {}
    fps = v["fps"]
    evs = d["events"]
    cuts = d["hard_cuts"]
    lg = I18N.lang()                    # the reader's language: the app's in a job, English from the command line
    title = f"MotionLab - {d['name']}"
    p = []
    p.append(f"<!doctype html><html lang='{lg}'><head><meta charset='utf-8'><meta name='viewport' "
             f"content='width=device-width,initial-scale=1'><title>{E(title)}</title><style>{CSS}</style></head><body>")
    p.append("<header class='top'><div class='topin'>"
             f"<div class='title'>{E(d['name'])} <span class='sub'>· {I18N.t('MotionLab report')}</span></div>"
             f"<nav><a href='#overview'>{I18N.t('Overview')}</a><a href='#events'>{I18N.t('Events')}</a>"
             f"<a href='#cards'>{I18N.t('Cards')}</a><a href='#misses'>{I18N.t('Possible misses')}</a>"
             f"<a href='#cuts'>{I18N.t('Hard cuts')}</a><a href='#feedback'>{I18N.t('Feedback')}</a></nav>"
             f"<span class='progress' id='prog'></span><button class='btn' id='theme'>{I18N.t('Theme')}</button>"
             "</div></header><main>")

    # ---------------- header
    src = d["source"]
    p.append("<section class='block' id='overview'><h1>" + E(d["name"]) + "</h1>")
    p.append("<div class='sub'>" + I18N.t(
        "{category} · analyzed {when} · analysis id <span class='mono'>{id}</span> · source verified unchanged: "
        "<b>{ok}</b>", category=E(I18N.t(style_label(d.get("category") or d.get("style")))), when=E(d["generated"]),
        id=E(d["analysis_id"]), ok=I18N.t("yes") if src.get("unchanged") else I18N.t("NO - check")) + "</div>")
    p.append("<div class='grid3' style='margin-top:14px'>")
    rot = " " + I18N.t("(rotated {deg}°)", deg=v["rotation"]) if v.get("rotation") else ""
    rate = I18N.t("VFR → analyzed on CFR proxy") if v["vfr"] else I18N.t("constant (CFR)")
    dur = I18N.t("{s}s · {n} frames", s=_n(v["duration_s"], ".2f", lg), n=v["frames"])
    hdr = " · " + I18N.t("HDR (tone-mapped for analysis)") if v.get("hdr") else ""
    p.append(f"<div><h3>{I18N.t('Video')}</h3><dl class='kv'>"
             f"<dt>{I18N.t('File')}</dt><dd class='mono'>{E(src['path'])}</dd>"
             f"<dt>{I18N.t('Resolution')}</dt><dd>{v['display_width']}×{v['display_height']}{rot}</dd>"
             f"<dt>{I18N.t('Frame rate')}</dt><dd>{fps:g} fps · {rate}</dd>"
             f"<dt>{I18N.t('Duration')}</dt><dd>{dur}</dd>"
             f"<dt>{I18N.t('Codec')}</dt><dd>{E(str(v.get('codec')))} {E(str(v.get('pix_fmt') or ''))}{hdr}</dd>"
             f"<dt>{I18N.t('Timecode')}</dt><dd>{E(v['timecode_note'])}</dd></dl></div>")
    if a.get("available"):
        none = I18N.t("none found")
        drops = ", ".join(f"f{round(x['frame'])} ({E(x['tc'])})" for x in a.get("drops", [])) or none
        builds = ", ".join(f"f{x['start_frame']}-{x['end_frame']}" for x in a.get("builds", [])) or none
        tempo = I18N.t("<b>{bpm} BPM</b> · beat every {n} frames", bpm=_n(a["bpm"], ".1f", lg),
                       n=_n(a.get("beat_period_frames") or 0, ".2f", lg))
        beats = I18N.t("{n} (downbeats best-effort, confidence {c})", n=len(a.get("beats", [])),
                       c=_n(a.get("downbeat_confidence", 0), ".2f", lg))
        tol = d["on_beat_tolerance"]
        rule = I18N.tn(tol, "within ±{tol} frame of a beat", "within ±{tol} frame of a beat", tol=_n(tol, "g", lg))
        p.append(f"<div><h3>{I18N.t('Audio')}</h3><dl class='kv'>"
                 f"<dt>{I18N.t('Tempo')}</dt><dd>{tempo}</dd>"
                 f"<dt>{I18N.t('Beats')}</dt><dd>{beats}</dd>"
                 f"<dt>{I18N.t('Drops')}</dt><dd>{drops}</dd><dt>{I18N.t('Builds')}</dt><dd>{builds}</dd>"
                 f"<dt>{I18N.t('On-beat rule')}</dt><dd>{rule}</dd></dl></div>")
    else:
        p.append(f"<div><h3>{I18N.t('Audio')}</h3><p class='sub'>"
                 f"{I18N.t('No usable audio track: no beats or drops.')}</p></div>")
    prim, stack = {}, {}
    for ev in evs:
        if ev["final"].get("false_alarm"):
            continue
        pf = taxonomy.family(ev["final"]["type"])
        prim[pf] = prim.get(pf, 0) + 1
        for t in ev["final"]["types"][1:]:
            sf = taxonomy.family(t)
            if sf != pf:
                stack[sf] = stack.get(sf, 0) + 1
    p.append(f"<div><h3>{I18N.t('Effects found')}</h3><div class='counts'>")
    hc, hs = prim.get("Hard cut", 0), stack.get("Hard cut", 0)
    hc_note = ""
    if hc or hs:
        hc_note = " <span class='sub'>" + (
            I18N.t("({plain} plain + {events} in events, +{stacked} stacked)", plain=len(cuts), events=hc, stacked=hs)
            if hs else I18N.t("({plain} plain + {events} in events)", plain=len(cuts), events=hc)) + "</span>"
    p.append(f"<div><span>{I18N.t('Hard / jump cuts')}</span><b>{len(cuts) + hc}{hc_note}</b></div>")
    for f_ in taxonomy.FAMILIES:
        if f_ != "Hard cut" and (prim.get(f_) or stack.get(f_)):
            extra = " <span class='sub'>" + I18N.t("(+{n} stacked)", n=stack[f_]) + "</span>" if stack.get(f_) else ""
            p.append(f"<div><span>{E(I18N.t(f_))}</span><b>{prim.get(f_, 0)}{extra}</b></div>")
    p.append("</div><p class='note'>" + I18N.t(
        "{events} events · {shots} shots · average shot {avg}s. “Stacked” = the effect also occurs inside another "
        "event (e.g. motion blur inside a zoom transition).", events=len(evs), shots=len(d["shots"]),
        avg=_n(d["avg_shot_s"], ".2f", lg)) + "</p></div>")
    p.append("</div>")
    ov = "overview.png"
    p.append(f"<h3>{I18N.t('Signals over time')}</h3><div class='overview fit' id='ovwrap'><picture>"
             "<source srcset='overview_dark.png' media='(prefers-color-scheme: dark)'>"
             f"<img src='{ov}' alt='{E(I18N.t('per-frame metrics over time with beats and detected events'))}'>"
             "</picture></div><div class='row'><button class='btn' id='fit' "
             "onclick=\"document.getElementById('ovwrap').classList.toggle('fit')\">"
             f"{I18N.t('Fit width / actual size')}</button><span class='note'>"
             + I18N.t("Thin vertical lines = beats, darker = bar starts, red = drop. Bottom lane = events (IDs match "
                      "the cards).") + "</span></div>")
    p.append("<p class='note'>" + I18N.t(
        "Frame numbers are 0-based (frame 0 = first frame). Every number can be checked on the contact sheets: each "
        "tile shows its frame number and timecode. In Resolve, a timeline usually starts at 01:00:00:00 - add one hour "
        "to these timecodes, or set the timeline start to 00:00:00:00.") + "</p></section>")

    # ---------------- events table
    p.append(f"<section class='block' id='events'><h2>{I18N.t('Events')}</h2><div class='tablewrap'><table><thead><tr>"
             + _th(I18N.t("ID"), I18N.t("Type"), I18N.t("Frames"), I18N.t("Timecode"), I18N.t("Dur (f)"),
                   I18N.t("Beat"), I18N.t("Confidence"), I18N.t("Origin"), I18N.t("Review"), I18N.t("Your verdict"))
             + "</tr></thead><tbody>")
    for ev in evs:
        f_ = ev["final"]
        beat = _chip(I18N.t("on beat"), "yes") if f_.get("on_beat") else \
            ("—" if f_.get("on_beat") is None else I18N.t("off|beat"))
        if f_.get("on_drop"):
            beat += " " + _chip("drop", "drop")
        fa = " class='fa' style='text-decoration:line-through'" if f_.get("false_alarm") else ""
        rev = _chip(I18N.t("reviewed"), "yes") if ev.get("review") else _chip(I18N.t("auto draft"), "draft")
        p.append(f"<tr{fa}><td class='mono'><a href='#{ev['id']}'>{ev['id']}</a></td>"
                 f"<td>{E(I18N.t(taxonomy.label(f_['type'])))}{(' · ' + E(f_['sub'])) if f_.get('sub') else ''}</td>"
                 f"<td class='num'>{ev['start']}–{ev['end']}</td><td class='num'>{E(ev['tc_start'])}</td>"
                 f"<td class='num'>{ev['duration_frames']}</td><td>{beat}</td>"
                 f"<td>{_chip(_conf(f_['confidence']), f_['confidence'])}</td><td>{E(_origin(f_['origin']))}</td>"
                 f"<td>{rev}</td><td><span class='vstat' id='st-{ev['id']}'>—</span></td></tr>")
    if not evs:
        p.append(f"<tr><td colspan='10'>{I18N.t('No effects detected besides plain cuts.')}</td></tr>")
    p.append("</tbody></table></div></section>")

    # ---------------- possible misses: sudden changes no event explains (evidence only)
    near = d.get("near_misses") or []
    if near:
        p.append(f"<section class='block' id='misses'><h2>{I18N.t('Possible misses')}</h2><p class='sub'>"
                 + I18N.t("The strongest sudden changes that no event and no cut explains. Most are nothing (a light "
                          "change, fast motion); if one is an effect, write what it is and click <b>Add to missed "
                          "effects</b> - it goes into your feedback.") + "</p><div class='nm'>")
        what_ph, add = E(I18N.t("what is it? (optional)")), I18N.t("Add to missed effects")
        for n in near:
            f0 = n["frame"]
            where = f"f{f0} ({n['tc']})"
            imgs = "".join(f"<div><a href='{E(src)}' target='_blank'><img loading='lazy' src='{E(src)}' alt=''></a>"
                           f"<span>f{f0 - 1 + i}</span></div>" for i, src in enumerate(n.get("frames", [])))
            chk = ("<div class='note' style='margin:0 0 6px'>"
                   + I18N.t("<b>Claude checked:</b> {text}", text=E(n["checked"])) + "</div>" if n.get("checked") else "")
            p.append(f"<div class='nmi' data-where='{E(where)}'><div class='row' style='margin:0 0 6px'>"
                     f"<b class='mono'>{E(where)}</b><span class='note' style='margin:0'>{E(n['why'])}</span></div>{chk}"
                     f"<div class='fr3'>{imgs}</div><div class='row'><input placeholder='{what_ph}'>"
                     f"<button class='btn'>{add}</button></div></div>")
        p.append("</div></section>")

    # ---------------- cards: preview + what happens + measured evidence open; details folded; false alarms folded
    p.append("<div id='cards'>")
    for k, ev in enumerate(evs):
        f_ = ev["final"]
        rv = ev.get("review")
        fa = bool(f_.get("false_alarm"))
        badges = [_chip(I18N.t("{level} confidence", level=_conf(f_["confidence"])), f_["confidence"])]
        if f_.get("on_beat"):
            badges.append(_chip(I18N.t("on beat"), "yes"))
        if f_.get("on_drop"):
            badges.append(_chip(I18N.t("on the drop"), "drop"))
        badges.append(_chip(I18N.t("reviewed by Claude") if rv else I18N.t("auto draft - not reviewed yet"),
                            "yes" if rv else "draft"))
        if fa:
            badges.insert(0, _chip(I18N.t("false alarm - not an edit effect (Claude)"), "low"))
        cls = "card" + (" alt" if k % 2 else "") + (" fa" if fa else "")
        frames = I18N.tn(ev["duration_frames"], "{frames} frames", "{frames} frames", frames=ev["duration_frames"])
        p.append(f"<article class='{cls}' id='{ev['id']}'><div class='cardhead'><span class='id mono'>{ev['id']}</span>"
                 f"<span class='ty'>{E(I18N.t(taxonomy.label(f_['type'])))}</span>"
                 f"<span class='rng mono'>f{ev['start']}–{ev['end']} · {E(ev['tc_start'])} – {E(ev['tc_end'])} · "
                 f"{frames}</span>{''.join(badges)}")
        if fa:
            reason = (f_.get("what") or "").split(". ")[0][:260]
            p.append("<div class='fareason'>" + I18N.t("Why it is not an effect: {reason}", reason=E(reason)) + "</div>")
        p.append("</div>")
        if fa:
            p.append("<details class='fold facard'><summary>" + I18N.t(
                "Show the full card (optional - a false alarm needs no verdict; use “Agree with all false alarms” in "
                "Feedback)") + "</summary>")
        p.append("<div class='cardbody'><div>")
        if ev.get("preview"):
            vid = f"v-{ev['id']}"
            p.append(f"<video id='{vid}' src='{E(ev['preview'])}' loop muted playsinline controls preload='metadata' data-auto></video>"
                     f"<div class='speed' data-vid='{vid}'>{I18N.t('speed')} <button class='btn on' data-rate='1'>1×</button>"
                     f"<button class='btn' data-rate='0.5'>{_n(0.5, 'g', lg)}×</button>"
                     f"<button class='btn' data-rate='0.25'>{_n(0.25, 'g', lg)}×</button>"
                     f"<button class='btn' data-rate='0.1'>{_n(0.1, 'g', lg)}×</button></div>"
                     "<p class='note'>" + I18N.t("Preview f{a}–{b}; yellow bar = effect frames, frame number + timecode "
                                                 "burned in. Unmute for the beat.", a=ev["preview_range"][0],
                                                 b=ev["preview_range"][1]) + "</p>")
        p.append("</div><div class='desc'>")
        p.append(f"<h3 style='margin-top:0'>{I18N.t('What happens')}</h3><p>{E(f_['what'])}</p>")
        p.append(f"<h3>{I18N.t('Measured evidence')}</h3><ul>" + "".join(f"<li>{E(x)}</li>" for x in f_["evidence"])
                 + "</ul>")
        p.append("</div></div>")
        p.append(f"<details class='fold'><summary>{I18N.t('In depth: duration, timing, easing, origin and how to rebuild it')}"
                 "</summary><div class='in'><dl class='kv'>"
                 f"<dt>{I18N.t('Duration')}</dt><dd>{E(f_['duration_text'])}</dd>"
                 f"<dt>{I18N.t('Timing')}</dt><dd>{E(f_['timing'])}</dd>"
                 f"<dt>{I18N.t('Easing')}</dt><dd>{E(f_['easing'])}</dd>"
                 f"<dt>{I18N.t('Origin')}</dt><dd><b>{E(_origin(f_['origin']))}</b> — {E(f_['origin_why'])}</dd>")
        if ev.get("cuts"):
            p.append(f"<dt>{I18N.t('Cut')}</dt><dd class='mono'>{', '.join('f' + str(c) for c in ev['cuts'])}</dd>")
        if len(f_["types"]) > 1:
            p.append(f"<dt>{I18N.t('Stacked')}</dt>"
                     f"<dd>{E(', '.join(I18N.t(taxonomy.label(t)) for t in f_['types']))}</dd>")
        p.append(f"</dl><h3>{I18N.t('Rebuild in Resolve / Fusion')}</h3><div class='rebuild'>{E(f_['rebuild'])}</div>")
        if rv and rv.get("notes"):
            p.append("<p class='reviewed'>" + I18N.t("Reviewer note: {note}", note=E(rv["notes"])) + "</p>")
        p.append("</div></details>")
        sheets = ev.get("sheets", [])
        p.append("<details class='fold'><summary>" + I18N.tn(
            len(sheets), "Frame list: {n} contact sheet - every frame with its number and timecode",
            "Frame list: {n} contact sheets - every frame with its number and timecode")
            + "</summary><div class='in'><div class='sheets'>")
        for i, sh in enumerate(sheets, 1):
            alt = E(I18N.t("{id} contact sheet {i}", id=ev["id"], i=i))
            p.append(f"<a href='{E(sh)}' target='_blank'><img loading='lazy' src='{E(sh)}' alt='{alt}'></a>")
        p.append("</div></div></details>")
        notes_ph = E(I18N.t("Notes for {id} (what is wrong / what it really is)…", id=ev["id"]))
        p.append(f"<div class='verdict' data-ev='{ev['id']}'><div class='vbtns'>"
                 f"<button class='vbtn' data-v='correct'>✓ {I18N.t('Correct')}</button>"
                 f"<button class='vbtn' data-v='partly'>~ {I18N.t('Partly')}</button>"
                 f"<button class='vbtn' data-v='wrong'>✗ {I18N.t('Wrong')}</button></div>"
                 f"<textarea placeholder='{notes_ph}'></textarea></div>")
        if fa:
            p.append("</details>")
        p.append("</article>")
    p.append("</div>")

    # ---------------- hard cuts
    p.append(f"<section class='block' id='cuts'><h2>{I18N.t('Hard cuts')}</h2><p class='sub'>"
             + I18N.t("Plain cuts with nothing special (cuts that are part of an effect live in that effect's card). "
                      "Mark a row ✗ if it is not a real cut.")
             + "</p><div class='tablewrap'><table><thead><tr>"
             + _th(I18N.t("ID"), I18N.t("Frame"), I18N.t("Timecode"), I18N.t("Time"), I18N.t("Kind"), I18N.t("On beat"),
                   I18N.t("Offset (f)"), I18N.t("Bar.beat"), I18N.t("Shot before"), I18N.t("Before | after"),
                   I18N.t("Check"))
             + "</tr></thead><tbody>")
    note_ph = E(I18N.t("note"))
    for c in cuts:
        ob = c.get("on_beat")
        ob_txt = "—" if ob is None else ((I18N.t("yes, drop") if c.get("on_drop") else I18N.t("yes")) if ob else "no")
        off = "" if c.get("offset_frames") is None else _n(c["offset_frames"], "+.1f", lg)
        p.append(f"<tr><td class='mono'>{c['id']}</td><td class='num'>{c['frame']}</td><td class='num'>{E(c['tc'])}</td>"
                 f"<td class='num'>{_n(c['time_s'], '.3f', lg)}s</td><td>{E(_kind(c['kind']))}</td>"
                 f"<td>{_chip(ob_txt, 'yes' if ob else '')}</td>"
                 f"<td class='num'>{off}</td>"
                 f"<td class='num'>{E(str(c.get('bar_beat') or ''))}</td>"
                 f"<td class='num'>{c.get('shot_before_frames', '')} f</td>"
                 f"<td>{('<img class=cutthumb loading=lazy src=' + E(c['thumb']) + '>') if c.get('thumb') else ''}</td>"
                 f"<td><div class='cutv' data-cut='{c['id']}'><button class='vbtn' data-v='correct'>✓</button>"
                 f"<button class='vbtn' data-v='wrong'>✗</button><textarea class='cutnote' placeholder='{note_ph}'>"
                 "</textarea></div></td></tr>")
    if not cuts:
        p.append(f"<tr><td colspan='11'>{I18N.t('No plain hard cuts.')}</td></tr>")
    p.append("</tbody></table></div></section>")

    # ---------------- feedback
    eg = E(I18N.t("e.g. missed: speed ramp around f1210 / 00:00:40:10; the glitches in the chorus are all RGB split "
                  "+ slice"))
    p.append(f"<section class='block' id='feedback'><h2>{I18N.t('Feedback')}</h2><p class='sub'>"
             + I18N.t("Your verdicts are saved in this browser as you click. Add anything the analysis missed (with "
                      "frame numbers or timecodes), then generate the feedback text and paste it back to Claude.")
             + f"</p><h3>{I18N.t('Missed effects / general notes')}</h3>"
             f"<textarea id='missed' rows='4' placeholder='{eg}'></textarea>"
             f"<div class='row'><button class='btn' id='agreefa'>{I18N.t('Agree with all false alarms')}</button>"
             f"<span class='note'>{I18N.t('(optional: tells Claude its “not an effect” calls were right)')}</span></div>"
             f"<div class='row'><button class='btn' id='gen'>{I18N.t('Generate feedback')}</button>"
             f"<button class='btn' id='copy'>{I18N.t('Copy')}</button><span class='note' id='copymsg'></span>"
             f"<span style='flex:1'></span><button class='btn' id='reset'>{I18N.t('Clear all verdicts')}</button></div>"
             f"<textarea id='fbout' readonly placeholder='{E(I18N.t('Click “Generate feedback”.'))}'></textarea>"
             "</section>")

    js_data = {
        "analysis_id": d["analysis_id"], "video": d["name"], "fps": fps,
        "report_path": str(out).replace("\\", "/"),
        "events": [{"id": e["id"], "type": e["final"]["type"], "start": e["start"], "end": e["end"],
                    "tc_start": e["tc_start"], "tc_end": e["tc_end"], "fa": bool(e["final"].get("false_alarm"))}
                   for e in evs],
        "cuts": [{"id": c["id"], "frame": c["frame"], "tc": c["tc"]} for c in cuts],
        "saved": _saved_verdicts(out.parent / "feedback" / "verdicts.json"),
    }
    p.append("</main><script type='application/json' id='ml-data'>"
             + json.dumps(js_data).replace("</", "<\\/") + "</script>" + _js_words(lg) + "<script>" + JS
             + "</script></body></html>")
    out.write_text("".join(p), encoding="utf-8")
