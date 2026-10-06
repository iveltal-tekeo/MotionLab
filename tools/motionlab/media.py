"""Frame extraction, contact sheets and looping preview MP4s (one sequential decode for everything)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .signals import fit_long_side, iter_frames
from .timecode import frame_to_tc
from .util import log, tool

FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def _font(names, size):
    for n in names:
        p = FONT_DIR / n
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                pass
    return ImageFont.load_default()


def fonts(scale: float = 1.0):
    return {
        "mono": _font(["consola.ttf", "cour.ttf"], int(15 * scale)),
        "mono_b": _font(["consolab.ttf", "consola.ttf"], int(15 * scale)),
        "small": _font(["consola.ttf"], int(13 * scale)),
        "title": _font(["segoeuib.ttf", "arialbd.ttf"], int(22 * scale)),
        "body": _font(["segoeui.ttf", "arial.ttf"], int(15 * scale)),
    }


ACCENT = (255, 196, 0)      # event frames
PAD_COL = (120, 120, 120)   # padding frames
CUT_COL = (255, 80, 80)
BEAT_COL = (80, 200, 255)


# ----------------------------------------------------------------------------- planning
def plan(events: list[dict], N: int, fps: float, cfg: dict) -> dict:
    sc, pc, pad = cfg["sheets"], cfg["preview"], cfg["events"]["pad_frames"]
    plans = {}
    for ev in events:
        a, b = max(0, ev["start"] - pad), min(N - 1, ev["end"] + pad)
        frames = list(range(a, b + 1))
        sampled = False
        if len(frames) > sc["max_full_extract_frames"]:
            k, step = sc["long_event_edge_frames"], sc["long_event_sample_step"]
            mid = list(range(a + k, b - k + 1, step))
            frames = sorted(set(range(a, a + k)) | set(mid) | set(range(b - k + 1, b + 1)))
            sampled = True
        ctx = max(pad, int(round(pc["context_seconds"] * fps)))
        pa, pb = max(0, ev["start"] - ctx), min(N - 1, ev["end"] + ctx)
        need = int(round(pc["min_seconds"] * fps)) - (pb - pa + 1)
        if need > 0:
            pa, pb = max(0, pa - need // 2 - need % 2), min(N - 1, pb + need // 2)
        pb = min(pb, pa + int(20 * fps))
        plans[ev["id"]] = {"sheet_frames": frames, "sampled": sampled, "window": [a, b], "preview": [pa, pb]}
    return plans


# ----------------------------------------------------------------------------- labels
def _tile_label(i, ev, fps, drop, marks):
    tc = frame_to_tc(i, fps, drop)
    flags = []
    if i in marks.get("cuts", ()):
        flags.append("CUT")
    if i in marks.get("drop", ()):
        flags.append("DROP")
    elif i in marks.get("downbeat", ()):
        flags.append("BAR")
    elif i in marks.get("beat", ()):
        flags.append("BEAT")
    return f"f{i}  {tc}", ev.get("labels", {}).get(i, "") or ev.get("labels", {}).get(str(i), ""), flags


def draw_preview_overlay(img: Image.Image, i: int, ev: dict, fps: float, drop: bool, marks: dict, F) -> Image.Image:
    d = ImageDraw.Draw(img)
    w, h = img.size
    line1, line2, flags = _tile_label(i, ev, fps, drop, marks)
    inside = ev["start"] <= i <= ev["end"]
    d.rectangle([0, 0, w, 24], fill=(0, 0, 0))
    d.text((6, 3), line1, font=F["mono_b"], fill=ACCENT if inside else (230, 230, 230))
    x = w - 6
    for fl in reversed(flags):
        tw = d.textlength(fl, font=F["mono_b"])
        col = CUT_COL if fl == "CUT" else (BEAT_COL if fl in ("BEAT", "BAR") else (255, 120, 255))
        d.rectangle([x - tw - 8, 2, x, 22], fill=col)
        d.text((x - tw - 4, 3), fl, font=F["mono_b"], fill=(0, 0, 0))
        x -= tw + 12
    if line2:
        d.text((6 + d.textlength(line1, font=F["mono_b"]) + 14, 3), line2, font=F["mono"], fill=(200, 200, 200))
    # effect bar at the bottom: shows where the event is inside the looping preview
    if inside:
        d.rectangle([0, h - 8, w, h], fill=ACCENT)
        d.text((6, h - 30), f"{ev['id']} {ev['type_label']}", font=F["mono_b"], fill=ACCENT,
               stroke_width=2, stroke_fill=(0, 0, 0))
    return img


# ----------------------------------------------------------------------------- decode + render
def flash_look(cur: np.ndarray, before: np.ndarray, fc: dict) -> dict | None:
    """What a flash lights up, on grey 0-255 frames: the area that got brighter than the frame before the flash by
    more than look_diff_min levels (largest blob), its level and its texture (std of the area minus a blur of
    ~12 px at 1520 wide). A flat solid frame has texture ~0; an over-exposed picture keeps its texture (4AM: flat
    0.3-1.2, textured 3.8-23 at 640 px wide)."""
    m = ((cur - before) > fc.get("look_diff_min", 40)).astype(np.uint8)
    n, _, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = (int(v) for v in st[i, :4])
    if w * h < 0.01 * cur.size:
        return None
    reg = cur[y + h // 10:y + h - h // 10, x + w // 10:x + w - w // 10]
    tex = float(np.std(reg - cv2.GaussianBlur(reg, (0, 0), max(2.0, 12.0 * cur.shape[1] / 1520))))
    return {"area_pct": round(100.0 * w * h / cur.size, 1), "level_pct": round(100.0 * float(reg.mean()) / 255, 1),
            "texture": round(tex, 2), "flat": tex < fc.get("look_flat_texture", 2.5)}


def look_note(lk: dict, flat_below: float) -> str:
    what = (("a flat, solid frame at " + f"{lk['level_pct']}%" + (" - pure white" if lk["level_pct"] >= 97 else
             " (light grey: give this level, not 'white')")) if lk["flat"] else
            f"an over-exposed picture at about {lk['level_pct']}% that keeps its texture - not a solid colour")
    return (f"flash look: the lit area ({lk['area_pct']}% of the frame) is {what} "
            f"(texture {lk['texture']}; flat = below {flat_below:g})")


def extract_and_render(video: Path, info: dict, events: list[dict], plans: dict, out_dir: Path,
                       fps: float, wav: Path | None, audio_offset: float, marks: dict, cfg: dict,
                       drop_tc: bool, guard, extra_frames=()) -> None:
    v = info["video"]
    ex = cfg["extract"]
    w, h = fit_long_side(v["display_aspect"], ex["width_px"])
    frames_dir = guard.check(out_dir / "frames")
    frames_dir.mkdir(parents=True, exist_ok=True)
    ev_dir = guard.check(out_dir / "events")
    ev_dir.mkdir(parents=True, exist_ok=True)
    need = {int(f) for f in extra_frames if f >= 0}             # e.g. frames of the possible misses
    for p in plans.values():
        need.update(p["sheet_frames"])
    starts = {}
    for ev in events:
        starts.setdefault(plans[ev["id"]]["preview"][0], []).append(ev)
    last_needed = max([max(p["sheet_frames"] + [p["preview"][1]]) for p in plans.values()] + list(need), default=-1)
    if last_needed < 0:
        return
    F = fonts(1.0)
    open_pipes = {}
    pc = cfg["preview"]
    cut_set = set(marks.get("cuts", ()))
    # flash look: measured on the peak frame of every flash component against the frame before the flash
    looks: dict[int, list] = {}
    for ev in events:
        for c in ev.get("components") or []:
            pk = (c.get("evidence") or {}).get("peak_frame")
            if c.get("type") in ("flash", "flash_white") and pk is not None and c["start"] >= 1:
                looks.setdefault(int(pk), []).append((ev, c))
    befores = {c["start"] - 1 for lst in looks.values() for _, c in lst}
    kept: dict[int, np.ndarray] = {}

    def start_pipe(ev):
        pa, pb = plans[ev["id"]]["preview"]
        out = guard.check(ev_dir / ev["id"] / "preview.mp4")
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [tool("ffmpeg"), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
               "-r", f"{fps:.6f}", "-i", "-"]
        if wav and wav.exists():
            t0 = max(0.0, pa / fps - audio_offset)
            cmd += ["-ss", f"{t0:.4f}", "-t", f"{(pb - pa + 1) / fps:.4f}", "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(pc["crf"]), "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", "-shortest", str(out)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        open_pipes[ev["id"]] = (p, ev, pb)

    log(f"extracting {len(need)} sheet frames and {len(events)} previews at {w}x{h}")
    q = ex["jpeg_quality"]
    for i, frame in iter_frames(video, w, h, v.get("hdr", False)):
        rgb = np.ascontiguousarray(frame[..., ::-1])
        if i in need:
            Image.fromarray(rgb).save(frames_dir / f"f{i:06d}.jpg", quality=q)
        if i in befores or i in looks:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
            if i in befores:
                kept[i] = gray
            for ev, c in looks.get(i, []):
                b = kept.get(c["start"] - 1)
                lk = flash_look(gray, b, cfg["flash"]) if b is not None else None
                if lk:
                    c.setdefault("evidence", {})["look"] = lk
                    note = look_note(lk, cfg["flash"].get("look_flat_texture", 2.5))
                    c.setdefault("notes", []).append(note)
                    if isinstance((ev.get("auto") or {}).get("evidence"), list):
                        ev["auto"]["evidence"].append(note)
        for ev in starts.get(i, []):
            start_pipe(ev)
        done = []
        for eid, (p, ev, pb) in open_pipes.items():
            img = draw_preview_overlay(Image.fromarray(rgb.copy()), i, ev, fps, drop_tc,
                                       {**marks, "cuts": cut_set | set(ev.get("cuts", []))}, F)
            try:
                p.stdin.write(img.tobytes())
            except (BrokenPipeError, OSError):
                done.append(eid)
                continue
            if i >= pb:
                done.append(eid)
        for eid in done:
            p, _, _ = open_pipes.pop(eid)
            try:
                p.stdin.close()
            except OSError:
                pass
            p.wait()
        if i >= last_needed and not open_pipes:
            break
    for eid, (p, _, _) in list(open_pipes.items()):
        p.stdin.close()
        p.wait()


def build_sheets(ev: dict, pl: dict, out_dir: Path, fps: float, drop_tc: bool, aspect: float, marks: dict,
                 cfg: dict, guard) -> list[str]:
    sc = cfg["sheets"]
    frames = pl["sheet_frames"]
    per = sc["max_frames_per_sheet"]
    cols = 4 if aspect >= 1.3 else (5 if aspect >= 0.8 else 6)
    W = sc["width_px"]
    gap = 6
    tw = (W - (cols + 1) * gap) // cols
    th = int(round(tw / aspect))
    lab_h = 40
    head_h = 58
    F = fonts(1.0)
    paths = []
    chunks = [frames[k:k + per] for k in range(0, len(frames), per)]
    cuts = set(marks.get("cuts", ())) | set(ev.get("cuts", []))
    for si, chunk in enumerate(chunks):
        rows = (len(chunk) + cols - 1) // cols
        H = head_h + rows * (th + lab_h + gap) + gap
        sheet = Image.new("RGB", (W, H), (18, 18, 20))
        d = ImageDraw.Draw(sheet)
        title = f"{ev['id']}  {ev['type_label']}" + (f"  ({ev['sub']})" if ev.get("sub") else "")
        d.text((gap + 4, 6), title, font=F["title"], fill=(255, 255, 255))
        rng = (f"effect f{ev['start']}-{ev['end']}  ({frame_to_tc(ev['start'], fps, drop_tc)} - "
               f"{frame_to_tc(ev['end'], fps, drop_tc)}), {ev['duration_frames']} frames"
               f"   |   sheet {si + 1}/{len(chunks)}   |   yellow = effect frames, grey = 3-frame padding"
               + ("   |   long event: edges complete, middle sampled" if pl["sampled"] else ""))
        d.text((gap + 4, 34), rng, font=F["small"], fill=(190, 190, 190))
        for k, i in enumerate(chunk):
            r, c = divmod(k, cols)
            x = gap + c * (tw + gap)
            y = head_h + r * (th + lab_h + gap)
            p = out_dir / "frames" / f"f{i:06d}.jpg"
            if p.exists():
                im = Image.open(p).convert("RGB").resize((tw, th), Image.LANCZOS)
                sheet.paste(im, (x, y))
            inside = ev["start"] <= i <= ev["end"]
            col = ACCENT if inside else PAD_COL
            d.rectangle([x - 2, y - 2, x + tw + 1, y + th + 1], outline=col, width=2)
            line1, line2, flags = _tile_label(i, ev, fps, drop_tc, {**marks, "cuts": cuts})
            d.rectangle([x, y + th + 2, x + tw, y + th + lab_h - 2], fill=(34, 34, 38))
            d.text((x + 5, y + th + 4), line1, font=F["mono_b"], fill=col if inside else (170, 170, 170))
            if line2:
                d.text((x + 5, y + th + 21), line2, font=F["mono"], fill=(230, 230, 230))
            fx = x + tw - 4
            for fl in reversed(flags):
                fw = d.textlength(fl, font=F["small"])
                fc = CUT_COL if fl == "CUT" else (BEAT_COL if fl in ("BEAT", "BAR") else (255, 120, 255))
                d.rectangle([fx - fw - 6, y + th + 21, fx, y + th + 37], fill=fc)
                d.text((fx - fw - 3, y + th + 22), fl, font=F["small"], fill=(0, 0, 0))
                fx -= fw + 10
        out = guard.check(out_dir / "events" / ev["id"] / f"sheet_{si + 1:02d}.jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out, quality=90)
        paths.append(str(out.relative_to(out_dir)).replace("\\", "/"))
    return paths


def cut_thumbs(thumbs, cut_frames: list[int], out_dir: Path, guard) -> dict:
    """Tiny before/after pair for every plain cut (from the cached thumbnails, no decode)."""
    d = guard.check(out_dir / "cuts")
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    N = len(thumbs)
    for c in cut_frames:
        if c <= 0 or c >= N:
            continue
        a = np.asarray(thumbs[c - 1])[..., ::-1]
        b = np.asarray(thumbs[c])[..., ::-1]
        pair = np.concatenate([a, np.full((a.shape[0], 3, 3), 255, np.uint8), b], axis=1)
        p = d / f"cut_{c:06d}.png"
        Image.fromarray(pair).save(p)
        out[c] = str(p.relative_to(out_dir)).replace("\\", "/")
    return out
