"""The platforms' safe zones on an upright video (2026-10-27, the user: "safe-zone guides on vertical videos showing
where TikTok, Reels and Shorts put their buttons and captions ... add the safe-zone guides in general when creating or
editing with claude vertical videos so important stuff dont get caught? search online for good safezones recent
ones"): where each app draws its own tabs, buttons, name, caption and progress bar over a 9:16 video - words, faces,
logos and products never go there.

None of the three publishes one for normal posts (only for ads, whose bottom is taller - a call-to-action button):
these are the middle of the 2026 guides' measures on 1080 x 1920 - TikTok top 108-220 / bottom 320-484 / right
140-180 (the For You tabs, the name + caption + sound, the like / comment / save / share column), Instagram Reels top
220-250 / bottom 320-430 / right 120-130, YouTube Shorts top ~200-380 / bottom 380-390 / right 120-201 (the newer
player's column with its labels). "all" = the strictest of the three: what the build's check flags (precheck
SAFE_BANDS, facefit's safe height), what the Editor shows first and what Claude keeps clear. A longer caption on the
post takes more of the bottom: these leave room for about three lines. Scaled to any other upright size.

    ZONES                       platform -> {label, top, bottom, left, right, rail: (y0, y1)} in px on 1080 x 1920
    upright(W, H)               a video the apps show full screen (9:16-ish, taller than 1.6:1)
    bands(platform, W, H)       {"top", "bottom", "right rail": (x0, y0, x1, y1)} - where the app draws over it
    safe_rect(platform, W, H)   (x0, y0, x1, y1): inside every band and the side margins - keep what matters in here
    for_page(W, H)              the Editor's guides: [{id, label, safe, bands}] (all first), None for another shape
"""
from __future__ import annotations

REF_W, REF_H = 1080, 1920
ZONES = {
    "tiktok": {"label": "TikTok", "top": 150, "bottom": 440, "left": 60, "right": 140, "rail": (720, 1640)},
    "reels": {"label": "Instagram Reels", "top": 220, "bottom": 420, "left": 60, "right": 130, "rail": (1000, 1700)},
    "shorts": {"label": "YouTube Shorts", "top": 200, "bottom": 380, "left": 60, "right": 200, "rail": (820, 1640)},
}
ZONES["all"] = {"label": "All three", **{k: max(z[k] for z in ZONES.values()) for k in ("top", "bottom", "left", "right")},
                "rail": (min(z["rail"][0] for z in ZONES.values()), max(z["rail"][1] for z in ZONES.values()))}
ORDER = ("all", "tiktok", "reels", "shorts")


def upright(W: float, H: float) -> bool:
    return W > 0 and H / W >= 1.6


def _z(platform: str) -> dict:
    if platform not in ZONES:
        raise ValueError(f"no safe zone for {platform!r} (one of {', '.join(ORDER)})")
    return ZONES[platform]


def bands(platform: str = "all", W: float = REF_W, H: float = REF_H) -> dict:
    z, sx, sy = _z(platform), W / REF_W, H / REF_H
    return {"top": (0, 0, W, round(z["top"] * sy)), "bottom": (0, round(H - z["bottom"] * sy), W, H),
            "right rail": (round(W - z["right"] * sx), round(z["rail"][0] * sy), W, round(z["rail"][1] * sy))}


def safe_rect(platform: str = "all", W: float = REF_W, H: float = REF_H) -> tuple:
    z, sx, sy = _z(platform), W / REF_W, H / REF_H
    return (round(z["left"] * sx), round(z["top"] * sy), round(W - z["right"] * sx), round(H - z["bottom"] * sy))


def for_page(W: float, H: float) -> list | None:
    if not upright(W, H):
        return None
    return [{"id": k, "label": ZONES[k]["label"], "safe": list(safe_rect(k, W, H)),
             "bands": {n: list(b) for n, b in bands(k, W, H).items()}} for k in ORDER]


def selfcheck() -> dict:
    import time
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok = ok and bool(cond)
        lines.append(f"{'PASS' if cond else 'FAIL'} {name}")

    a = ZONES["all"]
    case("all three = the strictest of each margin, the rail as tall as any",
         (a["top"], a["bottom"], a["right"], a["rail"]) == (220, 440, 200, (720, 1700)))
    case("the bands and the safe area on 1080x1920", bands("all") == {"top": (0, 0, 1080, 220), "bottom": (0, 1480, 1080, 1920),
         "right rail": (880, 720, 1080, 1700)} and safe_rect("all") == (60, 220, 880, 1480))
    case("scaled to 720x1280", safe_rect("tiktok", 720, 1280) == (40, 100, 627, 987))
    case("only an upright video has them", for_page(1920, 1080) is None and for_page(1080, 1350) is None
         and [g["id"] for g in for_page(1080, 1920)] == list(ORDER))
    return {"passed": ok, "seconds": round(time.time() - t0, 3), "lines": lines}


if __name__ == "__main__":
    r = selfcheck()
    print("\n".join(r["lines"]), "\nPASS" if r["passed"] else "\nFAIL")
