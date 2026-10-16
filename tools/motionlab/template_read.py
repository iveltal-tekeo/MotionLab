"""Reading a pack of captured template clips (0.5.0): the measuring half of motionlab\templates.py (numpy,
OpenCV, Pillow - the app never imports it; tools\templates.py read does). What is measured and where it goes:
templates.py's docstring."""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .colour import palette
from .media import fonts
from .signals import iter_frames
from .templates import (ALIVE_SHARE, CUT_SHARE, DIFF_LEVEL, GAP_FRAMES, HOLD_FRAMES, MOVE_SHARE, PAGE,
                        STILL_FRAMES, VIDEO_EXT, describe, guard, humanise, rel, root, split_name)
from .timecode import frame_to_tc
from .util import LAB, log, safe_name, sha256_file, write_json


def _probe(video: Path) -> dict:
    import subprocess
    from .util import tool
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames:format=duration", "-of", "json",
                          str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    j = json.loads(out.stdout or "{}")
    st = (j.get("streams") or [{}])[0]

    def rate(s):
        try:
            a, b = str(s).split("/")
            return float(a) / float(b) if float(b) else 0.0
        except (ValueError, ZeroDivisionError):
            return 0.0
    fps = rate(st.get("avg_frame_rate")) or rate(st.get("r_frame_rate")) or 25.0
    return {"width": int(st.get("width") or 0), "height": int(st.get("height") or 0), "fps": round(fps, 3),
            "duration": float((j.get("format") or {}).get("duration") or 0)}


def _ease(c: np.ndarray) -> str:
    """The ease word for one move from its change per frame (see the docstring)."""
    if len(c) < 4 or c.sum() <= 0:
        return "too short to tell"
    x = np.arange(len(c)) / (len(c) - 1)
    p = float((x * c).sum() / c.sum())
    if c.max() / max(c.mean(), 1e-9) < 1.35:
        return "linear"
    if p < 0.42:
        return "decelerating (slow end)"
    if p > 0.58:
        return "accelerating (slow start)"
    return "S-curve"


def measure(video: Path) -> tuple[dict, dict]:
    """(info, motion) of one clip - one decode, a half-size grey copy."""
    info = _probe(video)
    W, H = info["width"], info["height"]
    if not W or not H:
        raise ValueError(f"{video.name}: no picture")
    w2, h2 = max(2, W // 2 // 2 * 2), max(2, H // 2 // 2 * 2)
    change, mean, boxes = [0.0], [0.0], [None]
    first = prev = last = None
    n = 0
    for i, fr in iter_frames(video, W, H):
        g = cv2.cvtColor(cv2.resize(fr, (w2, h2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.int16)
        if prev is not None:
            d = np.abs(g - prev)
            m = d > DIFF_LEVEL
            change.append(float(m.mean()))
            mean.append(float(d.mean()))
            if m.any():
                ys, xs = np.nonzero(m)
                boxes.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
            else:
                boxes.append(None)
        else:
            first = g
        prev = last = g
        n = i + 1
    info["frames"] = n
    c = np.array(change[:n] if n else [0.0])
    fps = info["fps"] or 25.0
    moving = c > MOVE_SHARE
    moving[0] = False
    cuts = [int(t) for t in np.nonzero(c > CUT_SHARE)[0]]
    # moves: runs of moving frames, short gaps joined, cuts left out (a cut is its own event)
    runs, t = [], 1
    while t < n:
        if moving[t] and t not in cuts:
            s = t
            e = t
            while t < n:
                if moving[t] and t not in cuts:
                    e, t = t, t + 1
                    continue
                g = t
                while g < n and not moving[g] and g - e <= GAP_FRAMES:
                    g += 1
                if g < n and moving[g] and g not in cuts and g - e <= GAP_FRAMES + 1:
                    t = g
                    continue
                break
            runs.append((s, e))
        t += 1
    moves = []
    for s, e in runs:
        seg = c[s:e + 1]
        pk = s + int(np.argmax(seg))
        bx = [b for b in boxes[s:e + 1] if b]
        box = None
        if bx:
            x0, y0 = min(b[0] for b in bx), min(b[1] for b in bx)
            x1, y1 = max(b[2] for b in bx), max(b[3] for b in bx)
            box = [round(100 * x0 / w2, 1), round(100 * y0 / h2, 1), round(100 * (x1 + 1) / w2, 1),
                   round(100 * (y1 + 1) / h2, 1)]
        moves.append({"start": s, "end": e, "frames": e - s + 1, "fastest": pk, "peak_share": round(float(c[pk]), 4),
                      "ease": _ease(seg), "box_pct": box,
                      "start_tc": frame_to_tc(s, fps), "end_tc": frame_to_tc(e, fps)})
    # holds: the still runs between (and around) the moves
    busy = np.zeros(n, bool)
    for m in moves:
        busy[m["start"]:m["end"] + 1] = True
    for k in cuts:
        busy[k] = True
    holds, t = [], 0
    while t < n:
        if not busy[t]:
            s = t
            while t < n and not busy[t]:
                t += 1
            if t - s >= HOLD_FRAMES:
                hc = c[s:t]
                holds.append({"start": s, "end": t - 1, "frames": t - s, "start_tc": frame_to_tc(s, fps),
                              "end_tc": frame_to_tc(t - 1, fps),
                              "alive": round(float(((hc > ALIVE_SHARE) & (hc <= MOVE_SHARE)).mean()), 2)})
        t += 1
    loops = bool(first is not None and last is not None and n > STILL_FRAMES
                 and float((np.abs(last - first) > DIFF_LEVEL).mean()) < MOVE_SHARE * 5)
    moving_share = float(busy.mean()) if n else 0.0
    hold_frames = sum(h["frames"] for h in holds)
    alive = (sum(h["alive"] * h["frames"] for h in holds) / hold_frames) if hold_frames else None
    lens = sorted(m["frames"] for m in moves)
    eases = {}
    for m in moves:
        if m["frames"] >= 4:
            eases[m["ease"]] = eases.get(m["ease"], 0) + 1
    motion = {
        "moves": moves, "holds": holds, "cuts": [{"f": k, "tc": frame_to_tc(k, fps)} for k in cuts],
        "loops": loops, "moving_share": round(moving_share, 3),
        "moves_per_s": round(len(moves) / (n / fps), 2) if n else 0,
        "median_move_frames": lens[len(lens) // 2] if lens else None,
        "longest_hold_frames": max((h["frames"] for h in holds), default=0),
        "alive_in_holds": None if alive is None else round(alive, 2),
        "first_move": moves[0]["start"] if moves else None,
        "settled": (moves[-1]["end"] + 1) if moves else 0,
        "eases": eases,
        "change": [round(float(x), 4) for x in c],
    }
    return info, motion


def _frames(video: Path, W: int, H: int, want: list[int]) -> dict[int, np.ndarray]:
    want_s, out = set(want), {}
    top = max(want_s) if want_s else -1
    for i, fr in iter_frames(video, W, H):
        if i in want_s:
            out[i] = fr[..., ::-1].copy()
        if i >= top:
            break
    return out


def tile_frames(it: dict, k: int = 16) -> list[int]:
    n, mo = it["frames"], it["motion"]
    pick = {0, n - 1}
    for m in mo["moves"]:
        pick.update((m["start"], m["fastest"], m["end"]))
    for c in mo["cuts"]:
        pick.update((max(c["f"] - 1, 0), c["f"]))
    pick = sorted(p for p in pick if 0 <= p < n)
    if len(pick) > k:
        idx = np.linspace(0, len(pick) - 1, k).round().astype(int)
        pick = sorted({pick[i] for i in idx} | {0, n - 1})[:k]
    while len(pick) < min(8, n):
        gaps = [(pick[i + 1] - pick[i], i) for i in range(len(pick) - 1)]
        g, i = max(gaps)
        if g < 2:
            break
        pick.insert(i + 1, pick[i] + g // 2)
    return pick


def _label(d: ImageDraw.ImageDraw, x: int, y: int, text: str, F, fill=(235, 235, 235)) -> None:
    d.text((x, y), text, font=F, fill=fill)


def write_sheet(it: dict, video: Path, out: Path, col_w: int = 180) -> None:
    """The clip's contact sheet: tiles with frame + timecode, the change per frame below them (moves shaded)."""
    fps, n = it["fps"], it["frames"]
    picks = tile_frames(it)
    frs = _frames(video, it["width"], it["height"], picks)
    th = int(round(col_w * it["height"] / max(it["width"], 1)))
    cols = 4 if it["height"] >= it["width"] else 3
    cw = col_w if cols == 4 else int(col_w * 1.6)
    th = int(round(cw * it["height"] / max(it["width"], 1)))
    rows = math.ceil(len(picks) / cols)
    F = fonts(0.9)
    head, lab, gh = 30, 20, 110
    W = cols * cw + (cols + 1) * 6
    H = head + rows * (th + lab + 6) + gh + 30
    sh = Image.new("RGB", (W, H), (18, 18, 22))
    d = ImageDraw.Draw(sh)
    _label(d, 8, 6, f"{it['id']}  ·  {n} frames at {fps:g} fps  ·  {it['width']}x{it['height']}", F["mono_b"])
    for k, f in enumerate(picks):
        r, q = divmod(k, cols)
        x, y = 6 + q * (cw + 6), head + r * (th + lab + 6)
        im = frs.get(f)
        if im is not None:
            sh.paste(Image.fromarray(im).resize((cw, th), Image.LANCZOS), (x, y))
        _label(d, x + 2, y + th + 2, f"f{f} {frame_to_tc(f, fps)}", F["small"], (255, 210, 90))
    # the change per frame
    gy = head + rows * (th + lab + 6) + 18
    gx0, gx1 = 8, W - 8
    c = np.array(it["motion"]["change"] or [0.0])
    top = max(float(c.max()), MOVE_SHARE * 4)
    X = lambda t: gx0 + (gx1 - gx0) * t / max(n - 1, 1)                # noqa: E731
    for m in it["motion"]["moves"]:
        d.rectangle([X(m["start"]), gy, max(X(m["end"]), X(m["start"]) + 1), gy + gh - 10], fill=(40, 60, 90))
    for cu in it["motion"]["cuts"]:
        d.line([X(cu["f"]), gy, X(cu["f"]), gy + gh - 10], fill=(255, 80, 80), width=2)
    pts = [(X(t), gy + gh - 10 - (gh - 14) * min(float(v) / top, 1.0)) for t, v in enumerate(c)]
    if len(pts) > 1:
        d.line(pts, fill=(120, 220, 255), width=1)
    d.line([gx0, gy + gh - 10, gx1, gy + gh - 10], fill=(90, 90, 100))
    _label(d, gx0, gy - 16, "change per frame (moves shaded, cuts red)", F["small"], (160, 160, 170))
    _label(d, gx0, gy + gh - 6, f"f0 {frame_to_tc(0, fps)}", F["small"], (160, 160, 170))
    end = f"f{n - 1} {frame_to_tc(n - 1, fps)}"
    _label(d, gx1 - 8 * len(end), gy + gh - 6, end, F["small"], (160, 160, 170))
    sh.save(out, optimize=True)


def poster_frame(it: dict) -> int:
    holds = it["motion"]["holds"]
    if holds:
        h = max(holds, key=lambda h: (h["frames"], -h["start"]))
        return (h["start"] + h["end"]) // 2
    return it["frames"] // 2


def write_overviews(pack: str, items: list[dict], src_of) -> list[Path]:
    """PAGE clips a page, 6 tiles each (frame + timecode) - what Claude reads to write the cards."""
    out, F = [], fonts(0.85)
    d0 = guard(root() / pack)
    for old in d0.glob("overview_*.png"):
        old.unlink()
    for pg in range(math.ceil(len(items) / PAGE)):
        chunk = items[pg * PAGE:(pg + 1) * PAGE]
        tw = 112
        rows = []
        for it in chunk:
            th = int(round(tw * it["height"] / max(it["width"], 1)))
            n = it["frames"]
            mo = it["motion"]
            pick = [0]
            for m in mo["moves"][:5]:
                pick.append(m["fastest"])
            pick.append(poster_frame(it))
            pick.append(n - 1)
            pick = sorted(set(p for p in pick if 0 <= p < n))
            while len(pick) < min(6, n):
                gaps = [(pick[i + 1] - pick[i], i) for i in range(len(pick) - 1)]
                g, i = max(gaps)
                if g < 2:
                    break
                pick.insert(i + 1, pick[i] + g // 2)
            if len(pick) > 6:
                pick = [pick[i] for i in np.linspace(0, len(pick) - 1, 6).round().astype(int)]
            rows.append((it, pick, th))
        W = 6 + 6 * (tw + 6) + 250
        H = 6 + sum(th + 22 for _, _, th in rows)
        sh = Image.new("RGB", (W, H), (18, 18, 22))
        d = ImageDraw.Draw(sh)
        y = 6
        for it, pick, th in rows:
            frs = _frames(src_of(it), it["width"], it["height"], pick)
            for q, f in enumerate(pick):
                x = 6 + q * (tw + 6)
                if f in frs:
                    sh.paste(Image.fromarray(frs[f]).resize((tw, th), Image.LANCZOS), (x, y))
                _label(d, x, y + th + 2, f"f{f} {frame_to_tc(f, it['fps'])}", F["small"], (255, 210, 90))
            x = 6 + 6 * (tw + 6) + 4
            mo = it["motion"]
            lines = [f"#{it['n']} {it['kind']}", it["slug"][:30], f"{it['frames']} f · {it['seconds']:.1f} s",
                     f"{len(mo['moves'])} moves" + (" · loops" if mo["loops"] else ""),
                     f"moving {round(100 * mo['moving_share'])} %",
                     "a still capture" if it["still"] else ""]
            for k, ln in enumerate(lines):
                _label(d, x, y + 4 + k * 18, ln, F["mono_b"] if k == 0 else F["small"])
            y += th + 22
        p = d0 / f"overview_{pg + 1}.png"
        sh.save(p, optimize=True)
        out.append(p)
    return out


def read_pack(src: Path, pack: str | None = None, force: bool = False, only: list[str] | None = None) -> dict:
    """Measure every clip in src (a folder) into ROOT\\<pack>\\ - re-using a clip's numbers while its file is unchanged."""
    src = Path(src).resolve()
    if not src.is_dir():
        raise SystemExit(f"not a folder: {src}")
    pack = safe_name(pack or src.name).lower()
    d0 = guard(root() / pack)
    d0.mkdir(parents=True, exist_ok=True)
    pj = d0 / "pack.json"
    old = {}
    if pj.exists():
        old = {it["id"]: it for it in json.loads(pj.read_text(encoding="utf-8")).get("items", [])}
    clips = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT)
    if not clips:
        raise SystemExit(f"no video clips in {src}")
    items, changed = [], []
    for k, p in enumerate(clips, 1):
        tid, kind, slug = split_name(p.stem, pack)
        st = p.stat()
        sig = f"{p.name}:{st.st_size}:{st.st_mtime_ns}"
        o = old.get(tid)
        if only and tid not in only:
            if o:
                items.append(o)
            continue
        if o and o.get("sig") == sig and not force and (d0 / tid / "sheet.png").exists():
            items.append(o)
            continue
        sha = sha256_file(p)
        if o and o.get("sha256") and o["sha256"] != sha:
            changed.append(p.name)
        info, motion = measure(p)
        it = {"id": tid, "kind": kind, "slug": slug, "name": humanise(slug), "file": rel(p), "sha256": sha,
              "sig": sig, **{k2: info[k2] for k2 in ("frames", "fps", "width", "height")},
              "seconds": round(info["frames"] / (info["fps"] or 25), 2),
              "still": info["frames"] < STILL_FRAMES, "motion": motion}
        od = guard(d0 / tid)
        od.mkdir(parents=True, exist_ok=True)
        pf = poster_frame(it)
        fr = _frames(p, it["width"], it["height"], sorted({0, pf, it["frames"] // 3, (2 * it["frames"]) // 3}))
        if pf in fr:
            Image.fromarray(fr[pf]).save(od / "poster.jpg", quality=88)
        px = np.concatenate([v.reshape(-1, 3) for v in fr.values()]) if fr else np.zeros((1, 3), np.uint8)
        mid = fr.get(pf)
        bg = None
        if mid is not None:
            b = np.concatenate([mid[:4].reshape(-1, 3), mid[-4:].reshape(-1, 3), mid[:, :4].reshape(-1, 3),
                                mid[:, -4:].reshape(-1, 3)])
            bg = "#%02x%02x%02x" % tuple(int(v) for v in np.median(b, axis=0))
        it["colours"] = {"background": bg, "main": palette(px, 5)}
        it["poster_f"] = pf
        write_sheet(it, p, od / "sheet.png")
        items.append(it)
        log(f"[{k}/{len(clips)}] {tid}: {it['frames']} f, {len(motion['moves'])} moves, "
            f"{len(motion['holds'])} holds{' - a still capture' if it['still'] else ''}")
    items.sort(key=lambda it: (it["kind"], it["slug"]))
    for n, it in enumerate(items, 1):
        it["n"] = n
    kinds = {}
    for it in items:
        kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
    data = {"pack": pack, "source": rel(src), "read": _dt.date.today().isoformat(), "items": items, "kinds": kinds,
            "changed": changed}
    write_json(pj, data)
    pages = write_overviews(pack, items, lambda it: LAB / it["file"])
    log(f"{pack}: {len(items)} clips ({', '.join(f'{v} {k}' for k, v in sorted(kinds.items()))}), "
        f"{len(pages)} overview pages -> {rel(d0)}")
    if changed:
        log(f"WARNING: {len(changed)} clip(s) changed since the first read (SHA-256): {', '.join(changed)}")
    return data


def selfcheck(verbose: bool = True) -> dict:
    """A synthetic clip with known moves (ffmpeg draws a box that slides in, holds, slides out) - measured in a
    temp folder; PASS when the moves and the hold are found within 2 frames."""
    import subprocess
    import tempfile
    from .util import tool
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clip = td / "clips" / "test__box__slide.mp4"
        clip.parent.mkdir()
        # 60 frames at 25 fps: still 0-9, the box slides in over f10-f19 (linear), holds f20-f39, slides out f40-f49
        expr = "if(lt(n,10),-100,if(lt(n,20),-100+(n-9)*20,if(lt(n,40),100,if(lt(n,50),100+(n-39)*20,400))))"
        subprocess.run([tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x202030:s=320x320:r=25:d=2.4",
                        "-f", "lavfi", "-i", "color=c=0xffcc00:s=60x60:r=25:d=2.4", "-filter_complex",
                        f"[0][1]overlay=x='{expr}':y=130:eval=frame,format=yuv420p", "-frames:v", "60",
                        "-c:v", "libx264", "-crf", "12", str(clip)], check=True)
        os.environ["MOTIONLAB_TEMPLATES_ROOT"] = str(td / "packs")
        try:
            d = read_pack(clip.parent, "test")
        finally:
            os.environ.pop("MOTIONLAB_TEMPLATES_ROOT", None)
        it = d["items"][0]
        mv = it["motion"]["moves"]
        ok_moves = len(mv) == 2 and abs(mv[0]["start"] - 10) <= 2 and abs(mv[0]["end"] - 19) <= 2 \
            and abs(mv[1]["start"] - 40) <= 2 and abs(mv[1]["end"] - 49) <= 2
        hd = [h for h in it["motion"]["holds"] if h["start"] >= 15 and h["end"] <= 42]
        ok_hold = len(hd) == 1 and hd[0]["frames"] >= 17
        ok_files = (td / "packs" / "test" / it["id"] / "sheet.png").exists() and \
            (td / "packs" / "test" / "overview_1.png").exists()
        res = {"moves": ok_moves, "hold": ok_hold, "files": ok_files, "id": it["id"] == "box__slide"}
        if verbose:
            for ln in describe(it):
                print(ln)
            print("selfcheck:", "PASS" if all(res.values()) else f"FAIL {res}")
        return res
