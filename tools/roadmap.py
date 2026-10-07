"""Draw the MotionLab roadmap (docs\\roadmap.png): where the lab stands and where it goes, in the 4AM look
(pixel-font title, seven-segment date, grain). Edit STAGES / VERDICT / FOOTER below and re-run:

    .venv\\Scripts\\python tools\\roadmap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import graphics as G  # noqa: E402
from motionlab.util import LAB, setup_console  # noqa: E402

OUT = LAB / "docs" / "roadmap.png"
DATE = "2026-10-07"
W, H = 1920, 1080
BG = (13, 13, 15)
WHITE, GREY, DIM = (236, 236, 236), (128, 128, 132), (58, 58, 62)
AMBER = (255, 196, 0)
YOU_ARE_HERE_AFTER = 7                      # the marker sits between this stage and the next

# (title, status, maturity 0-5, big number, caption, details)
STAGES = [
    ("Foundation", "DONE", 4, "4/4", "self-tests pass",
     "analyse > sheets > review > report. Frame + timecode on everything. Your videos are never changed."),
    ("Detect effects", "WEAK", 1, "40%", "effect types right before review",
     "1 reference analysed (4AM). 0 false alarms, but 34 of 57 effects needed Claude's relabel."),
    ("Rebuild in the lab", "DONE", 3, "51/54", "key frames on time",
     "test_4am v1: your DJI footage in 4AM's style. Lab renderer: exact, not editable."),
    ("Rebuild in Resolve", "DONE", 4, "53/54", "key frames, 1.83/255 off v1",
     "Native timeline + Fusion you can edit. Same render after reopening. Spots your hand edits."),
    ("Feedback loop", "STARTED", 2, "44", "verdicts given (4AM)",
     "1 round on 4AM: 31 correct, 13 partly > lessons L001-L007, flash look, possible-misses list."),
    ("Effect library", "DONE", 3, "14", "effects saved, 10 macros",
     "Recipes + Fusion macros checked in Resolve against 4AM. Later: install them as Resolve templates."),
    ("MVP for friends", "STARTED", 3, "v0.2.5", "ready: you upload it",
     "Setup, auto-update, sharing. 0.2.5: review tab, red possible misses, Delete, Claude buttons with effort."),
    ("Share + specialise", "STARTED", 1, "1", "reference card (yours)",
     "Cards + lessons through GitHub, review step, packs, pacing per category. v0.3: 30 videos, category profiles."),
    ("Templates + macOS", "LATER", 0, "v0.5", "planned",
     "Use a reference as a template: its feel and pacing with your own story and music, not 1:1. A macOS app."),
]
VERDICT = [
    ("STRONG", "Measuring and rebuilding are frame-accurate and verified, in the lab and in DaVinci Resolve."),
    ("WEAK", "Detection has seen one video and one round of your feedback (7 lessons). Every accuracy number is "
             "anecdotal until ~10 references per category come with feedback."),
    ("NEXT", "You upload v0.2.5 to GitHub  >  friends clone + setup.bat  >  10 videos each with verdicts  >  Share  >  "
             "category profiles (v0.3)  >  templates by feel + macOS (v0.5)."),
]
FOOTER = ("risks: Resolve crashes on heavy Fusion (comps kept lean, watchdog)  |  footage cache = 2.6 GB per minute "
          "of footage (tools\\storage.py)  |  drawn by tools\\roadmap.py")


def font(name: str, size: int):
    return ImageFont.truetype(name, size)


def wrap(d: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


def paste_mask(img: np.ndarray, mask: np.ndarray, x: int, y: int, color, glow: float = 0.0, sigma: float = 6.0):
    h, w = mask.shape
    c = np.array(color, np.float32) / 255.0
    region = img[y:y + h, x:x + w]
    region[:] = region * (1 - mask[..., None]) + c * mask[..., None]
    if glow:
        pad = int(3 * sigma)
        m = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
        m[pad:pad + h, pad:pad + w] = mask
        b = cv2.GaussianBlur(m, (0, 0), sigma) * glow
        y0, x0 = y - pad, x - pad
        img[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] += b[..., None] * c


def main() -> int:
    setup_console()
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    f_num = font("consola.ttf", 17)
    f_title = font("segoeuib.ttf", 23)
    f_chip = font("consolab.ttf", 15)
    f_big = font("bahnschrift.ttf", 52)
    f_cap = font("segoeuib.ttf", 15)
    f_body = font("segoeui.ttf", 16)
    f_verdict = font("segoeuisl.ttf", 23)
    f_small = font("consola.ttf", 15)

    track_y, x0, x1 = 336, 160, 1770
    xs = [x0 + i * (x1 - x0) / (len(STAGES) - 1) for i in range(len(STAGES))]
    col_w = min(212, int((x1 - x0) / (len(STAGES) - 1)) - 12)
    # ---- track: solid where done, dashed amber for next, dotted grey for later
    for i in range(len(STAGES) - 1):
        a, b = xs[i] + 16, xs[i + 1] - 16
        st = STAGES[i + 1][1]
        if st in ("DONE", "WEAK"):
            d.line([(a, track_y), (b, track_y)], fill=WHITE, width=3)
        else:
            step, ln, col = (18, 10, AMBER) if st in ("NEXT", "STARTED") else (12, 3, GREY)
            x = a
            while x < b:
                d.line([(x, track_y), (min(x + ln, b), track_y)], fill=col, width=3)
                x += step
    # ---- stations
    for i, (title, status, mat, big, cap, body) in enumerate(STAGES):
        x = xs[i]
        col = {"DONE": WHITE, "WEAK": AMBER, "NEXT": AMBER, "STARTED": AMBER, "LATER": GREY}[status]
        r = 14
        if status == "DONE":
            d.ellipse([x - r, track_y - r, x + r, track_y + r], fill=WHITE)
        elif status == "WEAK":
            d.ellipse([x - r, track_y - r, x + r, track_y + r], outline=AMBER, width=4)
            d.ellipse([x - 5, track_y - 5, x + 5, track_y + 5], fill=AMBER)
        else:
            d.ellipse([x - r, track_y - r, x + r, track_y + r], outline=col, width=3, fill=BG)
        d.text((x, track_y - 42), f"{i + 1:02d}", font=f_num, fill=GREY, anchor="mm")
        left = int(x - col_w / 2)
        y = track_y + 34
        for ln in wrap(d, title.upper(), f_title, col_w):
            d.text((left, y), ln, font=f_title, fill=WHITE if status != "LATER" else (190, 190, 194))
            y += 29
        y = max(y, track_y + 98) + 4
        tw = d.textlength(status, font=f_chip)
        chip = [left, y, left + tw + 22, y + 26]
        if status == "DONE":
            d.rounded_rectangle(chip, 5, fill=(40, 40, 44), outline=WHITE, width=1)
        elif status == "WEAK":
            d.rounded_rectangle(chip, 5, fill=AMBER)
        else:
            d.rounded_rectangle(chip, 5, outline=col, width=2)
        d.text((left + 11, y + 13), status, font=f_chip, fill=BG if status == "WEAK" else col, anchor="lm")
        y += 40
        d.text((left - 2, y), big, font=f_big, fill=col if status != "DONE" else WHITE)
        y += 70
        for ln in wrap(d, cap, f_cap, col_w):
            d.text((left, y), ln, font=f_cap, fill=col if status != "DONE" else WHITE)
            y += 20
        y += 6
        for ln in wrap(d, body, f_body, col_w):
            d.text((left, y), ln, font=f_body, fill=(170, 170, 176))
            y += 22
        # maturity: 5 blocks
        by, bw = 772, col_w / 5
        for k in range(5):
            bx = left + k * bw
            if k < mat:
                d.rectangle([bx, by, bx + bw - 8, by + 9], fill=col if status != "DONE" else WHITE)
            else:
                d.rectangle([bx, by, bx + bw - 8, by + 9], outline=DIM, width=1)
    d.text((x0 - 106, 750), "maturity (0-5)", font=f_small, fill=GREY, anchor="lm")
    # ---- verdict band
    vy = 820
    d.rectangle([70, vy, W - 70, vy + 186], fill=(20, 20, 23))
    d.rectangle([70, vy, 76, vy + 186], fill=AMBER)
    yy = vy + 20
    for tag, text in VERDICT:
        col = {"STRONG": WHITE, "WEAK": AMBER, "NEXT": AMBER}[tag]
        tw = d.textlength(tag, font=f_chip)
        if tag == "WEAK":
            d.rounded_rectangle([104, yy + 2, 104 + tw + 22, yy + 28], 5, fill=AMBER)
            d.text((115, yy + 15), tag, font=f_chip, fill=BG, anchor="lm")
        else:
            d.rounded_rectangle([104, yy + 2, 104 + tw + 22, yy + 28], 5, outline=col, width=2)
            d.text((115, yy + 15), tag, font=f_chip, fill=col, anchor="lm")
        lines = wrap(d, text, f_verdict, W - 70 - 230 - 40)
        for k, ln in enumerate(lines):
            d.text((230, yy + k * 30), ln, font=f_verdict, fill=WHITE if tag != "WEAK" else (236, 226, 200))
        yy += max(1, len(lines)) * 30 + 22
    d.text((96, 1032), FOOTER, font=f_small, fill=(150, 150, 156))
    d.text((W - 96, 1032), "MotionLab  |  PC 2", font=f_small, fill=(150, 150, 156), anchor="ra")

    # ---- pixel-font title, seven-segment date, "you are here", grain + vignette (numpy)
    img = np.asarray(im, np.float32) / 255.0
    title = G.text_mask("MOTIONLAB", 62, width_scale=1.5)
    paste_mask(img, title, 70, 52, WHITE, glow=0.45, sigma=7)
    sub = G.text_mask("ROADMAP", 26, width_scale=1.5)
    paste_mask(img, sub, 74, 52 + title.shape[0] + 8, AMBER, glow=0.5, sigma=5)
    ghost = G.seg_mask("8888-88-88", 50)
    seg = G.seg_mask(DATE, 50)
    sx = W - 70 - seg.shape[1]
    paste_mask(img, ghost * 0.10, sx, 58, AMBER)
    paste_mask(img, seg, sx, 58, AMBER, glow=0.55, sigma=6)
    note = Image.new("RGB", (560, 30), BG)
    ImageDraw.Draw(note).text((560, 4), "where it stands and where it goes", font=f_small, fill=GREY, anchor="ra")
    nimg = np.asarray(note, np.float32) / 255.0
    img[58 + seg.shape[0] + 8:58 + seg.shape[0] + 38, W - 70 - 560:W - 70] = nimg
    mx = int((xs[YOU_ARE_HERE_AFTER - 1] + xs[YOU_ARE_HERE_AFTER]) / 2)
    yah = G.text_mask("YOU ARE HERE", 15, width_scale=1.3)
    paste_mask(img, yah, mx - yah.shape[1] // 2, track_y - 104, AMBER, glow=0.6, sigma=4)
    tri = np.zeros((26, 30), np.float32)
    cv2.fillPoly(tri, [np.array([[2, 2], [27, 2], [15, 22]], np.int32)], 1.0)
    tri = cv2.GaussianBlur(tri, (0, 0), 0.7)
    paste_mask(img, tri, mx - 15, track_y - 72, AMBER, glow=0.6, sigma=5)
    yy_, xx_ = np.mgrid[0:H, 0:W]
    vig = 1 - 0.30 * (((xx_ - W / 2) / (W / 2)) ** 2 + ((yy_ - H / 2) / (H / 2)) ** 2) ** 1.4
    img = img * np.clip(vig, 0, 1)[..., None]
    rng = np.random.default_rng(406)
    n = cv2.resize(G.grain((H // 2, W // 2), rng, 0.022), (W, H), interpolation=cv2.INTER_LINEAR)
    img = np.clip(img + n[..., None], 0, 1)
    OUT.parent.mkdir(exist_ok=True)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(OUT, optimize=True)
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
