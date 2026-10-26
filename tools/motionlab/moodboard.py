"""My Brand's mood board (0.6.0 step 7; planned as the Analyser's fourth way in, moved to My Brand > Style 2026-10-26 -
the user: "u can go ahead with the mood board for the my brand? or where should we put it?"): pictures the user likes
(saved from Pinterest or Instagram, screenshots, photos) as the brand's look. Each picture is COPIED into
knowledge\\local\\brand\\mood\\ (never shared; the original is only read) and measured like a thumbnail set's
(motionlab\\thumbsets.measure_picture: brightness, saturation, colourfulness, contrast, its main colours, faces, text)
+ its composition (how busy, how much empty space); the board's **style card** = the measures together in words and
its main colours. *For my brand* puts the card and the pictures' folder in Claude's brief (Claude opens the pictures),
and My Brand offers the board's colours as brand colours. Fetching a Pinterest board by its link is not done (the
platforms' terms; plans.md step 7).

    state() -> {"items": [{n, file, name, measures}], "card": {...} | None}
    add(name, data) -> the state after one picture (a raw body's bytes); remove(n); card_lines() -> the brief's lines
"""
from __future__ import annotations

import io
import json
import re
import threading
import time
from pathlib import Path

import numpy as np

from .util import LAB

DIR = Path(__import__("os").environ.get("MOTIONLAB_MOOD") or LAB / "knowledge" / "local" / "brand" / "mood")  # (tests)
INDEX = DIR / "mood.json"
EXT = (".jpg", ".jpeg", ".png", ".webp")
MAX_PICTURES = 40
MAX_BYTES = 25_000_000
_LOCK = threading.Lock()


def _load() -> dict:
    try:
        return json.loads(INDEX.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"items": [], "next": 1}


def _save(S: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    S["card"] = card(S["items"])
    INDEX.write_text(json.dumps(S, indent=1, ensure_ascii=False), encoding="utf-8")


def composition(path: Path) -> dict:
    """How busy a picture is and how much calm room it leaves: the share of its 16 x 16 cells with little detail
    (edge density under a calm line) = empty space; the mean edge density = busy; where its detail sits (thirds)."""
    import cv2
    from PIL import Image
    with Image.open(path) as im:
        g = np.asarray(im.convert("L").resize((256, max(16, round(256 * im.height / max(1, im.width))))), np.float32)
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    e = np.sqrt(gx * gx + gy * gy) > 40                      # (cv2.magnitude: not the same run to run - CLAUDE.md)
    H, W = e.shape
    cells = np.array([[e[i * H // 16:(i + 1) * H // 16, j * W // 16:(j + 1) * W // 16].mean() for j in range(16)]
                      for i in range(16)])
    ys, xs = np.nonzero(e)
    cy, cx = (float(ys.mean()) / H, float(xs.mean()) / W) if len(xs) else (0.5, 0.5)
    return {"busy": round(float(e.mean()), 3), "empty": round(float((cells < 0.04).mean()), 3),
            "detail_at": [round(cx, 3), round(cy, 3)]}


def state() -> dict:
    S = _load()
    return {"items": S["items"], "card": card(S["items"]), "max": MAX_PICTURES}     # (made again: the words may change)


def add(name: str, data: bytes) -> dict:
    """A picture the user picked (its bytes): copied in as NN_<name>, measured, the card made again."""
    from PIL import Image
    from . import thumbsets as TS
    stem, ext = Path(str(name)).stem, Path(str(name)).suffix.lower()
    if ext not in EXT:
        raise ValueError(f"{name}: not a picture ({', '.join(EXT)})")
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError("the picture is empty or bigger than 25 MB")
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
    except Exception:                                       # noqa: BLE001 - any broken picture
        raise ValueError(f"{name}: not a picture") from None
    with _LOCK:
        S = _load()
        if len(S["items"]) >= MAX_PICTURES:
            raise ValueError(f"a mood board holds {MAX_PICTURES} pictures - remove some first")
        import hashlib
        sha = hashlib.sha256(data).hexdigest()
        if any(it.get("sha256") == sha for it in S["items"]):
            return {**state(), "kept": True}                # the same picture twice: once
        n = int(S.get("next") or 1)
        clean = re.sub(r"[^\w.\- ]", "_", stem).strip(" .")[:60] or "picture"
        f = DIR / f"{n:02d}_{clean}{'.jpg' if ext == '.jpeg' else ext}"
        DIR.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data)
        m = TS.measure_picture(f)
        m.update(composition(f))
        S["items"].append({"n": n, "file": f.name, "name": stem[:80], "sha256": sha, "measures": m,
                           "added": time.strftime("%Y-%m-%d")})
        S["next"] = n + 1
        _save(S)
    return state()


def remove(n: int) -> dict:
    """A picture off the board (its copy stays in the folder until the user deletes it: never deleted here)."""
    with _LOCK:
        S = _load()
        S["items"] = [it for it in S["items"] if int(it["n"]) != int(n)]
        _save(S)
    return state()


def _word(v: float | None, lo: float, hi: float, words: tuple[str, str, str]) -> str | None:
    if v is None:
        return None
    return words[0] if v < lo else words[2] if v > hi else words[1]


def card(items: list[dict]) -> dict | None:
    """The board's style card: its main colours (thumbsets.main_colours over the pictures' palettes), and in words
    its light, colour, contrast, how busy, faces and text."""
    from . import thumbsets as TS
    rows = [it for it in items if it.get("measures")]
    if not rows:
        return None
    s = TS.summarise([{"n": it["n"], "measures": it["measures"]} for it in rows])
    M = [it["measures"] for it in rows]
    med = lambda k: float(np.median([m[k] for m in M if m.get(k) is not None])) if any(m.get(k) is not None for m in M) else None   # noqa: E731
    busy, empty = med("busy"), med("empty")
    words = [w for w in (                                   # (thumbnail.look: L* 0-100, saturation %, contrast in L*)
        _word(s.get("brightness"), 35, 62, ("dark and moody", "mid-tone", "bright and airy")),
        _word(s.get("saturation"), 20, 45, ("muted colours", "natural colours", "vivid colours")),
        _word(s.get("contrast"), 40, 70, ("soft contrast", "medium contrast", "punchy contrast")),
        _word(empty, 0.3, 0.55, ("full frames", "some room", "lots of empty space")),
        _word(busy, 0.06, 0.14, ("clean and simple", "some detail", "busy and detailed"))) if w]
    f, t = s.get("faces"), s.get("text") or {}
    return {"n": len(rows), "colours": (s.get("colours") or [])[:6], "words": words,
            "brightness": s.get("brightness"), "saturation": s.get("saturation"), "contrast": s.get("contrast"),
            "busy": busy, "empty": empty,
            "faces": None if f is None else {"with": f["with"], "of": f["known"]},
            "text": {"with": t.get("with", 0), "of": t.get("of", len(rows)), "where": (t.get("where") or {}).get("most")}}


def card_lines() -> list[str]:
    """For my brand's brief: the board in a line Claude acts on, with where its pictures are."""
    c = state()["card"]
    if not c:
        return []
    cols = ", ".join(f"{x['hex']} ({x['word']}, in {x['pictures']} of {c['n']})" for x in c["colours"])
    people = (f"people in {c['faces']['with']} of {c['faces']['of']}" if c.get("faces") else "")
    text = (f"words on {c['text']['with']} of {c['text']['of']}" + (f", mostly {c['text']['where']}"
                                                                     if c["text"].get("where") else "")) if c.get("text") else ""
    return [f"- **Their mood board** ({c['n']} pictures they chose as the brand's look - open them: "
            f"`{DIR.relative_to(LAB) if DIR.is_relative_to(LAB) else DIR}\\`): " + "; ".join(x for x in (", ".join(c["words"]), cols and "its colours " + cols,
                                                                         people, text) if x)
            + ". Match its feel in the graphics, the grade and the thumbnails (light, colour, contrast, room) - never "
              "copy a picture."]


def selfcheck() -> dict:
    """Pictures made here (no files of the user's): a calm pale one and a busy dark one -> measured, the card's words
    and colours; the same picture twice kept once; one removed."""
    import tempfile
    from PIL import Image
    global DIR, INDEX
    t0, lines, ok = time.time(), [], True

    def case(name, cond):
        nonlocal ok
        ok &= bool(cond)
        lines.append(("PASS " if cond else "FAIL ") + name)
    old = DIR, INDEX
    with tempfile.TemporaryDirectory(prefix="ml_mood_") as td:
        DIR, INDEX = Path(td) / "mood", Path(td) / "mood" / "mood.json"
        try:
            calm = np.full((540, 960, 3), (236, 228, 214), np.uint8)
            calm[200:340, 380:580] = (196, 120, 90)
            rng = np.random.default_rng(3)
            busy = (rng.integers(0, 90, (540, 960, 3))).astype(np.uint8)
            busy[::8] = 200
            pics = []
            for nm, a in (("calm.png", calm), ("busy.png", busy)):
                b = io.BytesIO()
                Image.fromarray(a).save(b, "PNG")
                pics.append((nm, b.getvalue()))
            add(*pics[0])
            st = add(*pics[1])
            again = add(*pics[0])
            items = st["items"]
            m0, m1 = items[0]["measures"], items[1]["measures"]
            case("two pictures copied and measured: the calm one emptier and less busy than the busy one",
                 len(items) == 2 and m0["empty"] > m1["empty"] and m0["busy"] < m1["busy"] and again.get("kept")
                 and len(again["items"]) == 2)
            c = st["card"]
            case(f"the style card: {', '.join(c['words'])}; colours {', '.join(x['word'] for x in c['colours'])}",
                 c["n"] == 2 and c["colours"] and len(c["words"]) >= 3)
            st = remove(items[1]["n"])
            case("one removed: the card made again from the other", len(st["items"]) == 1 and st["card"]["n"] == 1
                 and "bright and airy" in st["card"]["words"])
        finally:
            DIR, INDEX = old
    return {"passed": ok, "seconds": round(time.time() - t0, 2), "lines": lines}
