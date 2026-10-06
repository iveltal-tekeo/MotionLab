"""Draw the MotionLab app icon: amber pixel-font 'ML' (the logo's lettering) with a soft glow on a dark rounded
square. Writes tools\\motionlab\\app\\ui\\{favicon.png, icon-192.png, icon-512.png} and MotionLab.ico (16-256 px,
for the Desktop / Start-menu shortcut).

    .venv\\Scripts\\python tools\\app_icons.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from motionlab import graphics as G  # noqa: E402
from motionlab.util import LAB  # noqa: E402

UI = LAB / "tools" / "motionlab" / "app" / "ui"
AMBER = np.array([255, 196, 0], np.float32)            # --amber in app.css
BG = (22, 22, 26)


def draw(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.2), fill=BG + (255,))
    m = G.text_mask("ML", size * 0.34, stroke=size * 0.058, tracking=0.45, width_scale=1.1)
    ys, xs = np.nonzero(m > 0.01)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]           # the letters only (the mask has padding)
    k = min(1.0, size * 0.72 / m.shape[1])
    if k < 1:
        m = cv2.resize(m, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    h, w = m.shape
    canvas = np.zeros((size, size), np.float32)
    x0, y0 = (size - w) // 2, (size - h) // 2
    canvas[y0:y0 + h, x0:x0 + w] = m
    glow = cv2.GaussianBlur(canvas, (0, 0), size * 0.035) * 0.9
    rgb = np.asarray(img, np.float32)
    inside = rgb[..., 3:4] / 255.0
    for a, k in ((glow, 1.0), (canvas, 1.0)):
        rgb[..., :3] = rgb[..., :3] * (1 - a[..., None] * k * inside) + AMBER * a[..., None] * k * inside
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGBA")


def main() -> int:
    big = draw(1024)
    for name, px in (("icon-512.png", 512), ("icon-192.png", 192), ("favicon.png", 64)):
        big.resize((px, px), Image.LANCZOS).save(UI / name)
    big.save(LAB / "MotionLab.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icons written:", UI / "icon-512.png", LAB / "MotionLab.ico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
