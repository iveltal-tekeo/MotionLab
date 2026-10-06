"""Reference categories (what kind of video it is) and formats (its shape), so what the lab learns stays separable:
pacing, effects and lessons of music videos are not automatically right for cooking shorts or documentaries.

Every analysis has ONE category (picked in the app or `analyze.py --category`, stored in analysis\\<name>\\meta.json and
events.json "category"), any number of free tags ("instagram", "asmr" ...), and a format measured from the video itself
(vertical / horizontal / square; short <= 90 s, mid <= 10 min, long). A lesson applies to every category unless it says
`category: <id>` (the older `style: <id>` means the same)."""
from __future__ import annotations

CATEGORIES = {
    "music_video": "Music video",
    "ad": "Ad / creative / brand",
    "motion_graphics": "Motion graphics / animation",
    "documentary": "Documentary",
    "vlog": "Vlog",
    "tutorial": "Tutorial / how-to",
    "cooking": "Cooking / food",
    "podcast": "Podcast / talking head",
    "gaming": "Gaming",
    "sports": "Sports / fitness",
    "travel": "Travel",
    "fashion": "Fashion / beauty",
    "comedy": "Comedy / sketch",
    "trailer": "Trailer / teaser",
    "edit": "Fan edit / velocity / AMV",
    "other": "Other",
}
DEFAULT = "music_video"            # what the lab was built and tuned on (2026-10)
STYLES = CATEGORIES                # v0.2.0 name (events.json "style", lesson tag `style:`)
LEGACY = {"short": "other"}        # an early v0.2 category that became a format


def norm(category: str | None) -> str | None:
    if not category:
        return None
    category = LEGACY.get(category, category)
    return category if category in CATEGORIES else None


def label(category: str | None) -> str:
    return CATEGORIES.get(norm(category) or "", "Not set")


def fmt(width: int | None, height: int | None, duration_s: float | None) -> dict:
    """The video's shape: orientation from the display size; length short <= 90 s (reel-sized), mid <= 10 min, long."""
    w, h, d = int(width or 0), int(height or 0), float(duration_s or 0)
    if not w or not h:
        orient = "unknown"
    elif h > w * 1.15:
        orient = "vertical"
    elif w > h * 1.15:
        orient = "horizontal"
    else:
        orient = "square"
    length = "unknown" if d <= 0 else "short" if d <= 90 else "mid" if d <= 600 else "long"    # short = reel-sized
    names = {"vertical": "Vertical", "horizontal": "Horizontal", "square": "Square", "unknown": "?"}
    mm = f"{int(d // 60)}:{int(d % 60):02d}" if d > 0 else ""
    return {"orientation": orient, "length": length, "label": f"{names[orient]} · {mm}".strip(" ·")}


def clean_tags(tags) -> list[str]:
    if isinstance(tags, str):
        tags = tags.split(",")
    out = []
    for t in tags or []:
        t = "".join(ch for ch in str(t).strip().lower() if ch.isalnum() or ch in " -_")[:30].strip()
        if t and t not in out:
            out.append(t)
    return out[:12]
