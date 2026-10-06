"""Event detection: per-frame metrics -> effect components -> merged events.

Frame conventions (0-based, ranges inclusive):
  hard cut at c               c is the first frame of the new shot
  transitions / overlays      range = frames whose picture is affected (e.g. a crossfade's blended frames)
  motion effects              range = frames that moved relative to the previous frame
Every threshold lives in tools/config.json.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d

from . import taxonomy
from .timecode import frame_to_tc

NAN = float("nan")


# ----------------------------------------------------------------------------- helpers
def nz(x, v=0.0) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return np.where(np.isfinite(x), x, v)


def runs(mask) -> list[tuple[int, int]]:
    m = np.asarray(mask, dtype=np.int8)
    if m.size == 0:
        return []
    d = np.diff(np.concatenate(([0], m, [0])))
    s = np.where(d == 1)[0]
    e = np.where(d == -1)[0] - 1
    return [(int(a), int(b)) for a, b in zip(s, e)]


def merge_close(rs, gap: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for a, b in sorted(rs):
        if out and a - out[-1][1] - 1 <= gap:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def rmed(x, w: int) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    fill = float(np.nanmedian(x)) if np.isfinite(x).any() else 0.0
    return median_filter(np.where(np.isfinite(x), x, fill), size=max(1, int(w)), mode="nearest")


def med(x, a: int, b: int) -> float:
    a, b = max(0, int(a)), min(len(x) - 1, int(b))
    if b < a:
        return NAN
    seg = np.asarray(x[a:b + 1], dtype=np.float64)
    seg = seg[np.isfinite(seg)]
    return float(np.median(seg)) if len(seg) else NAN


def r1(x, nd=1):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def easing_from_steps(steps) -> str:
    """Guess easing from per-frame step sizes of a monotonic move (e.g. log-scale per frame)."""
    v = np.abs(np.asarray(steps, dtype=np.float64))
    v = v[np.isfinite(v)]
    if len(v) <= 1:
        return "instant (1 frame)"
    if len(v) == 2:
        return "accelerating (slow start)" if v[1] > 1.3 * v[0] else (
            "decelerating (slow end)" if v[0] > 1.3 * v[1] else "linear (constant speed)")
    t = np.linspace(0, 1, len(v))
    slope = np.polyfit(t, v / (v.mean() + 1e-12), 1)[0]
    peak = int(np.argmax(v))
    if 0 < peak < len(v) - 1 and v[peak] > 1.4 * max(v[0], v[-1]):
        return "S-curve (slow start and slow end)"
    if slope > 0.5:
        return "accelerating (slow start)"
    if slope < -0.5:
        return "decelerating (slow end)"
    return "linear (constant speed)"


def easing_from_progress(u) -> str:
    """Guess easing from a 0..1 progress curve sampled on the affected frames."""
    u = np.clip(np.asarray(u, dtype=np.float64), 0, 1)
    if len(u) < 3:
        return "too short to tell"
    steps = np.diff(np.r_[0.0, u, 1.0])
    return easing_from_steps(steps)


@dataclass
class Comp:
    type: str
    start: int
    end: int
    key: int
    score: float = 0.5
    sub: str = ""
    cut: int | None = None
    evidence: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    labels: dict = field(default_factory=dict)     # per-frame values for sheet tiles {frame: "text"}

    def as_dict(self):
        return {"type": self.type, "label": taxonomy.label(self.type), "sub": self.sub,
                "start": self.start, "end": self.end, "key": self.key, "score": round(self.score, 2),
                "cut": self.cut, "evidence": self.evidence, "notes": self.notes}


# ----------------------------------------------------------------------------- context
class Ctx:
    def __init__(self, metrics: dict, thumbs, fps: float, cfg: dict, drop_tc: bool = False):
        self.m = metrics
        self.th = thumbs
        self.fps = fps
        self.cfg = cfg
        self.drop = drop_tc
        self.N = len(metrics["frame"])
        self._thumb_stats()
        self.trans = np.zeros(self.N, bool)
        self.segments = [(0, self.N - 1)]
        self.seg_id = np.zeros(self.N, int)
        self.layout_changes: list[int] = []

    def set_segments(self, boundaries, trans: np.ndarray) -> None:
        """Shot segments split at cuts and at transition edges; `trans` marks transition frames."""
        self.trans = trans.copy()
        b = sorted({int(x) for x in boundaries if 0 < x < self.N})
        edges = [0] + b + [self.N]
        self.segments = [(s, e - 1) for s, e in zip(edges[:-1], edges[1:]) if e - 1 >= s]
        self.seg_id = np.zeros(self.N, int)
        for i, (s, e) in enumerate(self.segments):
            self.seg_id[s:e + 1] = i

    def clean_segments(self, min_len: int = 1):
        """Segments that are not transition frames (plain shot content)."""
        return [(s, e) for s, e in self.segments if e - s + 1 >= min_len and not self.trans[s:e + 1].all()]

    def fl(self, n) -> str:
        return f"f{int(n)} ({frame_to_tc(int(n), self.fps, self.drop)})"

    def fr(self, a, b) -> str:
        if a == b:
            return self.fl(a)
        return f"f{int(a)}-{int(b)} ({frame_to_tc(int(a), self.fps, self.drop)}-{frame_to_tc(int(b), self.fps, self.drop)})"

    def _thumb_stats(self):
        N = self.N
        self.tstd = np.zeros(N)
        self.hists = np.zeros((N, 16 * 8 + 16), np.float32)
        for a in range(0, N, 512):
            block = np.asarray(self.th[a:a + 512])
            for j, t in enumerate(block):
                g = cv2.cvtColor(t, cv2.COLOR_BGR2GRAY)
                self.tstd[a + j] = float(g.std())
                hsv = cv2.cvtColor(t, cv2.COLOR_BGR2HSV)
                h1 = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]).ravel()
                h2 = cv2.calcHist([hsv], [2], None, [16], [0, 256]).ravel()
                h1 /= max(float(h1.sum()), 1.0)
                h2 /= max(float(h2.sum()), 1.0)
                self.hists[a + j] = np.r_[0.5 * h1, 0.5 * h2]

    def hdist(self, i: int, j: int) -> float:
        i, j = int(np.clip(i, 0, self.N - 1)), int(np.clip(j, 0, self.N - 1))
        bc = float(np.sqrt(self.hists[i] * self.hists[j]).sum())
        return math.sqrt(max(0.0, 1.0 - bc))

    def thumb(self, i: int, sigma: float = 0.0) -> np.ndarray:
        t = np.asarray(self.th[int(np.clip(i, 0, self.N - 1))], dtype=np.float32)
        if sigma > 0:
            t = cv2.GaussianBlur(t, (0, 0), sigma)
        return t

    def corr(self, i: int, j: int) -> float:
        a = cv2.cvtColor(self.thumb(i), cv2.COLOR_BGR2GRAY).ravel()
        b = cv2.cvtColor(self.thumb(j), cv2.COLOR_BGR2GRAY).ravel()
        a, b = a - a.mean(), b - b.mean()
        den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
        return float((a * b).sum() / den) if den > 1e-6 else NAN

    def unchanged_textured(self, i: int, j: int) -> float:
        """Share of textured pixels of frame i that are (almost) identical in frame j. High for a split
        screen / overlay switching on (one part of the picture stays), ~0 for a real cut. Flat areas
        (letterbox bars, black backgrounds) are ignored."""
        a, b = self.thumb(i), self.thumb(j)
        g = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
        tex = cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)) > 20
        if tex.sum() < 30:
            return 0.0
        same = np.abs(a - b).max(axis=2) < 14
        return float(same[tex].mean())

    def edge_corr(self, i: int, j: int) -> float:
        """Correlation of edge maps: unchanged by brightness / colour / soft overlays (light leaks, grades),
        low when the picture content itself changes."""
        def edges(k):
            g = cv2.cvtColor(self.thumb(k).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
            g = (g - g.mean()) / (g.std() + 1e-6)
            return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)).ravel()
        a, b = edges(i), edges(j)
        a, b = a - a.mean(), b - b.mean()
        den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
        return float((a * b).sum() / den) if den > 1e-6 else NAN

    def aligned_hp_corr(self, i: int, j: int) -> float:
        """Fine-detail correlation between frames i < j after undoing the tracked camera translation.
        ~1 when frame j is the same picture (even under a light leak, grade or brightness change),
        ~0 when a different picture took over. NaN when the motion in between could not be tracked."""
        tx, ty = self.m["tx_pct"][i + 1:j + 1], self.m["ty_pct"][i + 1:j + 1]
        if j <= i or not (np.isfinite(tx).all() and np.isfinite(ty).all()):
            return NAN
        th, tw = self.th.shape[1:3]
        dx, dy = float(tx.sum()) / 100 * tw, float(ty.sum()) / 100 * th

        def hp(k):
            g = cv2.cvtColor(self.thumb(k).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
            return g - cv2.GaussianBlur(g, (0, 0), 3)
        a = hp(i)
        b = cv2.warpAffine(hp(j), np.float32([[1, 0, -dx], [0, 1, -dy]]), (tw, th),
                           borderMode=cv2.BORDER_CONSTANT, borderValue=float("nan"))
        valid = np.isfinite(b)
        valid[:4], valid[-4:], valid[:, :4], valid[:, -4:] = False, False, False, False
        if valid.sum() < 50:
            return NAN
        x, y = a[valid], b[valid]
        x, y = x - x.mean(), y - y.mean()
        den = math.sqrt(float((x * x).sum()) * float((y * y).sum()))
        return float((x * y).sum() / den) if den > 1e-6 else NAN

    def inverted(self, i: int, j: int) -> float:
        """Colour correlation of frame j with the NEGATIVE of frame i (~1 for an invert effect)."""
        a = (255.0 - self.thumb(i)).ravel()
        b = self.thumb(j).ravel()
        a, b = a - a.mean(), b - b.mean()
        den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
        return float((a * b).sum() / den) if den > 1e-6 else 0.0

    def same_shot(self, i: int, j: int) -> bool:
        """Do frames i and j show the same shot? (structure + colour similarity)"""
        if i < 0 or j >= self.N:
            return True
        c = self.corr(i, j)
        h = self.hdist(i, j)
        if np.isfinite(c) and min(self.tstd[i], self.tstd[j]) > 4:
            return c > 0.6 and h < 0.35
        return h < 0.25

    def speed(self, cut_frames=()) -> np.ndarray:
        """Translation speed per frame (% of width); 0 where it cannot be trusted (cuts, transitions)."""
        m = self.m
        rel = self.motion_reliable()
        lk = np.hypot(nz(m["tx_pct"]), nz(m["ty_pct"]))
        pc = np.hypot(nz(m["pc_tx_pct"]), nz(m["pc_ty_pct"]))
        v = np.where(rel, lk, np.where(nz(m["pc_resp"]) >= 0.15, pc, 0.0))
        v[self.trans] = 0.0
        for c in cut_frames:
            v[c] = 0.0
        return v

    def motion_reliable(self) -> np.ndarray:
        z = self.cfg["zoom"]
        m = self.m
        src = nz(m.get("motion_src", np.ones(self.N)), 1)
        lk = (src == 1) & (nz(m["motion_pts"]) >= z["min_pts"]) & (nz(m["motion_inliers"]) >= z["min_inliers"])
        fm = (src == 2)                       # Fourier-Mellin fallback already gated on its own confidence
        rel = (lk | fm) & np.isfinite(m["scale"]) & (self.tstd >= 3)
        return rel & ~self.trans


# ----------------------------------------------------------------------------- hard cuts
def detect_cuts(ctx: Ctx):
    c = ctx.cfg["cut"]
    m, N = ctx.m, ctx.N
    ch = nz(m["cut_hist"])
    fd = nz(m["frame_diff"])
    corr = nz(m["corr_prev"], 1.0)
    base_ch = rmed(ch, c["local_window"])
    base_fd = rmed(fd, c["local_window"])
    rel_ch = ch / (base_ch + 0.02)
    rel_fd = fd / (base_fd + 0.5)
    ok = np.zeros(N, bool)
    ok[1:] = (ctx.tstd[1:] >= c["min_thumb_std"]) & (ctx.tstd[:-1] >= c["min_thumb_std"])
    brk = np.where(ok, corr <= c["corr_max"], rel_fd >= c["fd_rel_min"])
    cand = (ch >= c["hist_min"]) & (rel_ch >= c["rel_min"]) & brk
    cand |= (ch >= c["hist_strong"]) & brk & (rel_fd >= c["fd_rel_min"])
    for t in np.where(cand & ok & (corr <= ctx.cfg["color"]["invert_corr_max"]))[0]:
        if ctx.inverted(t - 1, t) >= ctx.cfg["color"]["invert_match_min"]:
            cand[t] = False               # negative of the previous frame: an invert effect, not a new shot
    cand[0] = False
    idx = [int(t) for t in np.where(cand)[0]]
    # (a) part of the picture stays exactly the same -> overlay / split screen switching, not a cut
    partial = {t: ctx.unchanged_textured(t - 1, t) for t in idx}
    idx = [t for t in idx if partial[t] < c["partial_unchanged_min"]]
    # (b) two candidates one frame apart: keep the stronger, unless the middle frame is a 1-frame insert
    strength = {t: ch[t] * (1.0 - min(1.0, max(0.0, corr[t]))) for t in idx}
    drop = set()
    for t in idx:
        if t + 1 in strength and t not in drop:
            insert = ctx.same_shot(t - 1, t + 1)
            if not insert:
                drop.add(t if strength[t] < strength[t + 1] else t + 1)
    cuts = []
    for t in idx:
        if t in drop:
            continue
        cuts.append({"frame": int(t), "cut_hist": r1(ch[t], 3), "corr": r1(m["corr_prev"][t], 3),
                     "rel": r1(rel_ch[t], 1), "frame_diff": r1(fd[t], 1)})
    ctx.layout_changes = [t for t in partial if partial[t] >= c["partial_unchanged_min"]]

    # jump cuts: same framing/colours, isolated spike in pixel change not explained by camera motion
    jumps = []
    wr = nz(m["warp_resid"], NAN)
    base_wr = rmed(wr, c["local_window"])
    isset = set(int(x["frame"]) for x in cuts)
    for t in range(2, N - 1):
        if t in isset or not ok[t]:
            continue
        if rel_fd[t] < c["jump_cut_diff_rel"] or fd[t] < c["jump_cut_diff_min"] or corr[t] > c["jump_cut_corr_max"]:
            continue
        if fd[t - 1] > fd[t] / 3 or fd[t + 1] > fd[t] / 3:
            continue
        if np.isfinite(wr[t]) and wr[t] < 2.5 * (base_wr[t] + 0.5):
            continue          # global motion explains it
        jumps.append({"frame": t, "frame_diff": r1(fd[t], 1), "rel": r1(rel_fd[t], 1),
                      "corr": r1(m["corr_prev"][t], 3)})
    return cuts, jumps


# ----------------------------------------------------------------------------- flashes
def detect_flashes(ctx: Ctx) -> list[Comp]:
    f = ctx.cfg["flash"]
    m, N = ctx.m, ctx.N
    L = nz(m["luma_mean"])
    P05 = nz(m["luma_p05"])
    A = nz(m["lab_a"])
    B = nz(m["lab_b"])
    comps = []
    t = 1
    last_end = -1
    while t < N:
        rise1 = L[t] - L[t - 1]
        rise2 = L[t] - L[t - 2] if t >= 2 else 0.0
        if rise1 < 0.5 * f["luma_delta"] and rise2 < f["luma_delta"]:
            t += 1
            continue
        start = t if (rise1 >= 0.5 * f["luma_delta"] or t < 2 or L[t - 1] - L[t - 2] < 2.0) else t - 1
        if start <= last_end:              # the 2-frame attack check must not re-find the previous flash
            t += 1
            continue
        p = start + int(np.argmax(L[start:min(N, start + 3)]))
        u = p
        while u + 1 < N and (u - start) < f["max_frames"] + 2 and L[u + 1] < L[u] - 0.3:
            u += 1
        settle = med(L, u, u + 4)
        tol = max(1.0, 0.03 * settle)
        end = u - 1 if (u > p and L[u] <= settle + tol) else u
        before = med(L, start - 6, start - 1)
        after = med(L, end + 1, end + 6)
        base = np.nanmax([before, after])
        height = L[p] - base
        dur = end - start + 1
        if not (height >= f["luma_delta"] and dur <= f["max_frames"]):
            t += 1
            continue
        white = L[p] >= f["white_luma"] and P05[p] >= f["white_p05"]
        on_cut = not ctx.same_shot(start - 1, end + 1)
        comp = Comp("flash_white" if white else "flash", start, end, key=start, score=0.9 if white else 0.7)
        comp.sub = "on cut" if on_cut else "within shot"
        lum = {int(i): round(float(L[i]), 1) for i in range(max(0, start - 1), min(N, end + 2))}
        decay = [round(float(L[i]), 1) for i in range(p, end + 1)]
        comp.evidence = {"peak_frame": int(p), "peak_luma_pct": r1(L[p]), "luma_before_pct": r1(before),
                         "luma_after_pct": r1(after), "attack_frames": int(p - start + 1),
                         "decay_luma_pct": decay, "on_cut": on_cut}
        comp.notes.append(f"luma {r1(before)}% -> {r1(L[p])}% at {ctx.fl(p)} "
                          f"(p05 {r1(P05[p])}%), back to {r1(after)}% after {ctx.fl(end)}")
        comp.notes.append(f"attack {p - start + 1} frame(s), decay over {end - p} frame(s): "
                          + " -> ".join(f"{v}%" for v in decay))
        comp.notes.append("picture before and after the flash differ: flash hides a cut" if on_cut
                          else "same shot before and after: flash inside the shot")
        if on_cut:
            comp.cut = int(start)
        comp.labels = {k: f"L{v:.0f}%" for k, v in lum.items()}
        comps.append(comp)
        last_end = end
        t = max(t + 1, end + 1)            # always advance

    # colour flashes: short tint spikes in Lab a*/b*
    cd = ctx.cfg["color"]["ab_flash_delta"]
    t = 1
    while t < N - 1:
        base_a, base_b = med(A, t - 6, t - 1), med(B, t - 6, t - 1)
        d = math.hypot(A[t] - base_a, B[t] - base_b)
        if not np.isfinite(d) or d < cd:
            t += 1
            continue
        e = t
        while e + 1 < N and e - t < f["max_frames"] and math.hypot(A[e + 1] - base_a, B[e + 1] - base_b) >= cd * 0.5:
            e += 1
        aa, bb = med(A, e + 1, e + 6), med(B, e + 1, e + 6)
        if e - t + 1 <= f["max_frames"] and math.hypot(aa - base_a, bb - base_b) < cd * 0.5:
            pk = t + int(np.argmax([math.hypot(A[i] - base_a, B[i] - base_b) for i in range(t, e + 1)]))
            hue = math.degrees(math.atan2(B[pk] - base_b, A[pk] - base_a)) % 360
            comp = Comp("flash_color", t, e, key=t, score=0.6)
            comp.evidence = {"peak_frame": pk, "delta_ab": r1(math.hypot(A[pk] - base_a, B[pk] - base_b)),
                             "tint_hue_deg": r1(hue, 0), "a": r1(A[pk]), "b": r1(B[pk])}
            comp.notes.append(f"tint spike: Lab a*/b* moved {comp.evidence['delta_ab']} units "
                              f"(hue {comp.evidence['tint_hue_deg']} deg) at {ctx.fl(pk)}, back by {ctx.fl(e + 1)}")
            comps.append(comp)
            t = e + 1
        else:
            t += 1
    return comps


# ----------------------------------------------------------------------------- dips / fades
def detect_dips(ctx: Ctx) -> list[Comp]:
    d = ctx.cfg["dip"]
    m, N = ctx.m, ctx.N
    L = nz(m["luma_mean"])
    P95 = nz(m["luma_p95"], 100)
    P05 = nz(m["luma_p05"], 0)
    comps = []
    for kind in ("black", "white"):
        if kind == "black":
            ext = (L <= d["black_luma"]) & (P95 <= d["black_p95"])
            toward = lambda prev, cur: prev > cur + 0.3          # noqa: E731  (getting darker)
            away = lambda cur, nxt: nxt > cur + 0.3              # noqa: E731
        else:
            ext = (L >= d["white_luma"]) & (P05 >= d["white_p05"])
            toward = lambda prev, cur: prev < cur - 0.3          # noqa: E731
            away = lambda cur, nxt: nxt < cur - 0.3              # noqa: E731
        for a, b in runs(ext):
            if b - a + 1 > d["max_frames"]:
                continue
            s = a
            while s - 1 >= 0 and toward(L[s - 1], L[s]):
                s -= 1
            e = b
            while e + 1 < N and away(L[e], L[e + 1]):
                e += 1
            # s / e are the last plateau frame before / first plateau frame after the ramps
            pa = med(L, s - 5, s) if s > 0 else L[0]
            pb = med(L, e, e + 5) if e < N - 1 else L[N - 1]
            tola, tolb = max(1.0, 0.04 * pa), max(1.0, 0.04 * pb)
            if kind == "black":
                first = next((t for t in range(s, a + 1) if L[t] < pa - tola), a)
                last = next((t for t in range(e, b - 1, -1) if L[t] < pb - tolb), b)
                depth_ok = L[a:b + 1].min() <= d["min_depth_ratio"] * max(1.0, min(pa, pb)) or a == 0 or b == N - 1
            else:
                first = next((t for t in range(s, a + 1) if L[t] > pa + tola), a)
                last = next((t for t in range(e, b - 1, -1) if L[t] > pb + tolb), b)
                depth_ok = True
            if not depth_ok:
                continue
            ramp_l, ramp_r = a - first, last - b
            at_start, at_end = first == 0, last == N - 1
            if kind == "white" and ramp_l <= 1 and not at_start and \
                    (last - first + 1) <= ctx.cfg["flash"]["max_frames"]:
                continue                       # instant attack + short -> handled as a flash
            # black lead-in / tail that just cuts in or out (no ramp) is not a fade
            if at_start and not at_end and ramp_r < d["min_ramp_frames"]:
                continue
            if at_end and not at_start and ramp_l < d["min_ramp_frames"]:
                continue
            if ramp_l + ramp_r < d["min_ramp_frames"] and not (at_start or at_end):
                if kind == "black" and b - a + 1 <= 3:
                    comp = Comp("flash_black", first, last, key=a, score=0.7)
                    comp.notes.append(f"{b - a + 1} black frame(s) {ctx.fr(a, b)} with no fade ramps")
                    comp.cut = a if not ctx.same_shot(first - 1, last + 1) else None
                    comps.append(comp)
                continue
            typ = f"dip_{kind}"
            if at_start and kind == "black":
                typ = "fade_in"
            elif at_end and kind == "black":
                typ = "fade_out"
            transition = not ctx.same_shot(first - 1, last + 1) if 0 < first and last < N - 1 else False
            # the "hold" = frames at the extreme (within 1% of the darkest / brightest value)
            seg = L[first:last + 1]
            ext_v = seg.min() if kind == "black" else seg.max()
            hold = [first + i for i, v in enumerate(seg) if abs(v - ext_v) <= max(1.0, 0.02 * abs(ext_v))]
            h0, h1 = hold[0], hold[-1]
            comp = Comp(typ, first, last, key=h0, score=0.9)
            comp.sub = "transition (cut under the dip)" if transition else ("within shot" if 0 < first and last < N - 1 else "")
            comp.evidence = {"hold_frames_range": [h0, h1], "luma_min_pct" if kind == "black" else "luma_max_pct":
                             r1(ext_v), "luma_before_pct": r1(pa), "luma_after_pct": r1(pb),
                             "ramp_out_frames": int(h0 - first), "hold_frames": int(h1 - h0 + 1),
                             "ramp_in_frames": int(last - h1), "transition": transition}
            sign = 1 if kind == "black" else -1
            if h0 > first:
                comp.evidence["easing_out"] = easing_from_progress(
                    [sign * (pa - L[i]) / max(1e-6, sign * (pa - ext_v)) for i in range(first, h0)])
            if last > h1:
                comp.evidence["easing_in"] = easing_from_progress(
                    [sign * (pb - L[i]) / max(1e-6, sign * (pb - ext_v)) for i in range(last, h1, -1)][::-1])
            comp.notes.append(f"luma {r1(pa)}% -> {r1(ext_v)}% over {h0 - first} frame(s) ({ctx.fr(first, h0 - 1) if h0 > first else 'instant'}), "
                              f"held {h1 - h0 + 1} frame(s) {ctx.fr(h0, h1)}, back to {r1(pb)}% over "
                              f"{last - h1} frame(s) ({ctx.fr(h1 + 1, last) if last > h1 else 'instant'})")
            if comp.evidence.get("easing_out") or comp.evidence.get("easing_in"):
                comp.notes.append(f"fade out: {comp.evidence.get('easing_out', '-')}; fade in: {comp.evidence.get('easing_in', '-')}")
            if transition:
                comp.notes.append(f"different shot after the dip: a transition (new shot first visible at {ctx.fl(h1 + 1)})")
                comp.cut = int(min(h1 + 1, last))
            comp.labels = {i: f"L{L[i]:.0f}%" for i in range(max(0, first - 3), min(N, last + 4))}
            comps.append(comp)
    return comps


# ----------------------------------------------------------------------------- gradual transitions
def _progress(ctx: Ctx, ia: int, ib: int, frames: list[int]) -> np.ndarray:
    """Projection of each frame onto the A->B axis (1 = looks like frame ia, 0 = like frame ib)."""
    A = cv2.resize(ctx.thumb(ia, 1.5), (24, 14), interpolation=cv2.INTER_AREA).ravel()
    B = cv2.resize(ctx.thumb(ib, 1.5), (24, 14), interpolation=cv2.INTER_AREA).ravel()
    d = A - B
    den = float(d @ d) + 1e-6
    out = []
    for t in frames:
        F = cv2.resize(ctx.thumb(t, 1.5), (24, 14), interpolation=cv2.INTER_AREA).ravel()
        out.append(float((F - B) @ d / den))
    return np.asarray(out)


def _span(u: np.ndarray, frames: list[int], lo: float, hi: float):
    n = len(u)
    s = next((frames[i] for i in range(n - 1) if u[i] > lo and u[i + 1] > lo), None)
    e = next((frames[i] for i in range(n - 1, 0, -1) if u[i] < hi and u[i - 1] < hi), None)
    return s, e


def _geometry(P: np.ndarray, valid: np.ndarray, lumA: np.ndarray) -> dict:
    """Shape of a spatial transition from the per-pixel progress map P (0 = still A, 1 = already B)."""
    h, w = P.shape
    yy, xx = np.mgrid[0:h, 0:w]
    xs = (xx - (w - 1) / 2) / (w / 2)
    ys = (yy - (h - 1) / 2) / (h / 2)
    v = valid.ravel()
    target = (P.ravel()[v] > 0.5).astype(np.int8)
    if v.sum() < 30 or target.mean() in (0, 1):
        return {"kind": "none"}

    def best_split(proj):
        p = proj.ravel()[v]
        order = np.argsort(p)
        t_sorted = target[order]
        ones_left = np.cumsum(t_sorted)
        n = len(t_sorted)
        idx = np.arange(1, n + 1)
        acc_hi = ((idx - ones_left) + (t_sorted.sum() - ones_left)) / n      # B on the high side
        acc_lo = (ones_left + (n - idx - (t_sorted.sum() - ones_left))) / n  # B on the low side
        i_hi, i_lo = int(np.argmax(acc_hi)), int(np.argmax(acc_lo))
        return (float(acc_hi[i_hi]), +1) if acc_hi[i_hi] >= acc_lo[i_lo] else (float(acc_lo[i_lo]), -1)

    best = (0.0, 0, 0)
    for deg in range(0, 180, 15):
        th = math.radians(deg)
        acc, side = best_split(xs * math.cos(th) + ys * math.sin(th))
        if acc > best[0]:
            best = (acc, deg, side)
    r = np.hypot(xs, ys).ravel()[v]
    pv = P.ravel()[v]
    radial_corr = float(np.corrcoef(r, pv)[0, 1]) if pv.std() > 1e-6 else 0.0
    luma = float(np.corrcoef(lumA.ravel()[v], pv)[0, 1]) if pv.std() > 1e-6 else 0.0
    return {"kind": "geom", "plane_acc": best[0], "plane_deg": best[1], "plane_side": best[2],
            "radial_corr": radial_corr, "luma_corr": luma}


def detect_gradual(ctx: Ctx, cut_frames: set, claimed: np.ndarray) -> list[Comp]:
    tc = ctx.cfg["transition"]
    N, k = ctx.N, int(tc["stride"])
    if N < 2 * k + 4:
        return []
    H = ctx.hists
    G = np.zeros(N)
    bc = np.sqrt(H[:-2 * k] * H[2 * k:]).sum(axis=1)
    G[k:N - k] = np.sqrt(np.clip(1 - bc, 0, None))
    # comparisons that touch a flash / dip would merge it into a neighbouring transition
    for t in np.where(claimed)[0]:
        for u_ in (t - k, t, t + k):
            if 0 <= u_ < N:
                G[u_] = 0.0
    comps = []
    for r0, r1_ in runs(G >= tc["G_min"]):
        ia, ib = max(0, r0 - k), min(N - 1, r1_ + k)
        if any(ia <= c <= ib for c in cut_frames):
            continue
        frames = list(range(ia, ib + 1))
        p = _progress(ctx, ia, ib, frames)
        pa, pb = np.median(p[:3]), np.median(p[-3:])
        if abs(pa - pb) < 0.3:
            continue
        u = (pa - p) / (pa - pb)
        s, e = _span(u, frames, tc["lo"], tc["hi"])
        if s is None or e is None or e < s:
            continue
        # second pass with references right next to the transition (less motion drift)
        ia2, ib2 = max(0, s - 2), min(N - 1, e + 2)
        frames2 = list(range(ia2, ib2 + 1))
        p2 = _progress(ctx, ia2, ib2, frames2)
        pa2, pb2 = np.median(p2[:2]), np.median(p2[-2:])
        if abs(pa2 - pb2) > 0.3:
            u2 = (pa2 - p2) / (pa2 - pb2)
            s2, e2 = _span(u2, frames2, tc["lo"], tc["hi"])
            if s2 is not None and e2 is not None and e2 >= s2:
                s, e, u, frames = s2, e2, u2, frames2
        if e - s + 1 < tc["min_frames"] or e - s + 1 > tc["max_frames"]:
            continue
        if claimed[s:e + 1].mean() > 0.5:
            continue
        # same picture before and after (only colour / brightness changed): not a shot transition
        c_ab = ctx.corr(s - 1, e + 1)
        textured = min(ctx.tstd[s - 1], ctx.tstd[min(N - 1, e + 1)]) > 4
        if np.isfinite(c_ab) and textured and c_ab >= tc["same_picture_corr"]:
            continue
        e_ab = ctx.edge_corr(s - 1, e + 1)
        if np.isfinite(e_ab) and textured and e_ab >= tc["same_picture_edge_corr"]:
            continue                       # same edges: an overlay / grade on the same picture
        a_ab = ctx.aligned_hp_corr(s - 1, e + 1)
        if np.isfinite(a_ab) and a_ab >= tc["same_picture_aligned_corr"]:
            continue                       # same picture once the camera move is undone (leak / grade)
        if ctx.same_shot(s - 1, e + 1):
            continue
        ucur = np.array([u[frames.index(t)] for t in range(s, e + 1)])

        # classify from the per-pixel progress map at the middle of the transition:
        #   dissolve                    -> every pixel at the same progress (small spatial spread)
        #   wipe / iris / luma / shape  -> some areas already B, others still A (large spread)
        A = ctx.thumb(s - 1, 1.0)
        B = ctx.thumb(e + 1, 1.0)
        D = B - A
        den = (D * D).sum(axis=2)
        valid = np.abs(D).sum(axis=2) > tc["pixel_min_diff"]
        mids = [t for t in range(s, e + 1) if 0.3 <= u[frames.index(t)] <= 0.7] or [(s + e) // 2]
        spreads, maps = [], []
        for t in mids:
            F = ctx.thumb(t, 1.0)
            P = np.clip(((F - A) * D).sum(axis=2) / (den + 1e-6), -0.2, 1.2)
            maps.append(P)
            if valid.sum() > 20:
                spreads.append(float(P[valid].std()))
        spread = float(np.median(spreads)) if spreads else NAN
        tmid = mids[len(mids) // 2]
        Pm = maps[len(mids) // 2]
        geo = _geometry(Pm, valid, cv2.cvtColor(A.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)) \
            if valid.sum() > 20 else None
        spd = ctx.speed()[s:e + 1]
        typ, sub, notes = "crossfade", "", []
        if np.isfinite(spread) and spread >= tc["spread_spatial_min"] and geo and geo.get("kind") == "geom":
            if geo["plane_acc"] >= tc["wipe_plane_acc"]:
                typ = "wipe"
                deg = geo["plane_deg"] if geo["plane_side"] > 0 else (geo["plane_deg"] + 180) % 360
                sides = {0: "right", 90: "bottom", 180: "left", 270: "top"}
                nearest = min(sides, key=lambda a: min(abs(a - deg), 360 - abs(a - deg)))
                frm = sides[nearest] if min(abs(nearest - deg), 360 - abs(nearest - deg)) <= 20 else f"{deg:.0f} deg"
                sub = f"new shot enters from the {frm}" if frm in sides.values() else f"edge at {frm}"
                notes.append(f"some areas are already the new shot while others are still the old one "
                             f"(progress spread {spread:.2f}); the boundary is a straight edge "
                             f"(fit {geo['plane_acc']:.0%}): {sub}")
            elif abs(geo["radial_corr"]) >= tc["radial_corr_min"]:
                typ = "mask_reveal"
                outward = geo["radial_corr"] < 0
                sub = "iris / circle opening" if outward else "iris / circle closing"
                notes.append(f"the new shot appears {'from the centre outwards' if outward else 'from the edges inwards'} "
                             f"(progress vs distance from centre: corr {geo['radial_corr']:.2f}): {sub}")
            elif abs(geo["luma_corr"]) >= tc["luma_mask_corr_min"]:
                typ = "luma_fade"
                sub = "bright areas first" if geo["luma_corr"] > 0 else "dark areas first"
                notes.append(f"which pixels switch first follows the brightness of the outgoing shot "
                             f"(corr {geo['luma_corr']:.2f}): {sub}")
            else:
                typ = "mask_reveal"
                sub = "irregular shape"
                notes.append(f"the new shot appears region by region, not as a straight edge or circle "
                             f"(edge fit {geo['plane_acc']:.0%}, radial corr {geo['radial_corr']:.2f})")
        easing = easing_from_progress(ucur)
        if typ == "wipe" and geo["plane_deg"] in (0, 90):
            key = "seam_v_pos" if geo["plane_deg"] == 0 else "seam_h_pos"
            pos = nz(ctx.m[key], NAN)[s:e + 1]
            if np.isfinite(pos).all() and len(pos) >= 3 and abs(pos[-1] - pos[0]) > 0.3:
                prog = (pos - pos[0]) / (pos[-1] - pos[0])
                easing = easing_from_steps(np.diff(prog)) if len(prog) > 2 else easing
                notes.append("edge position per frame: " + ", ".join(f"{100 * x:.0f}%" for x in pos)
                             + f" ({easing})")
        if typ != "crossfade" and np.nanmedian(spd) >= tc["push_motion_min_pct"]:
            typ, sub = "push_slide", f"both pictures move {np.nanmedian(spd):.1f}% of the width per frame"
            notes.append(f"the outgoing and incoming pictures slide together ({sub})")
        if typ == "crossfade":
            notes.append(f"every pixel blends at the same rate (progress spread {spread:.2f} at the middle frame)")
        comp = Comp(typ, s, e, key=(s + e) // 2, score=0.85, sub=sub)
        comp.evidence = {"progress_spread_mid": r1(spread, 2), "progress": [round(float(x), 2) for x in ucur],
                         "easing": easing, "geometry": geo, "mid_frame": tmid,
                         "hist_change_A_to_B": r1(ctx.hdist(s - 1, e + 1), 2)}
        comp.notes = [f"shot A ({ctx.fl(s - 1)}) turns into shot B ({ctx.fl(e + 1)}) over {e - s + 1} frames "
                      f"{ctx.fr(s, e)}"] + notes
        comp.notes.append("progress per frame (0=A, 1=B): " + ", ".join(f"{x:.2f}" for x in ucur))
        comp.labels = {t: f"{100 * u[frames.index(t)]:.0f}%B" for t in frames if s - 3 <= t <= e + 3}
        comps.append(comp)
    return comps


def detect_slides(ctx: Ctx, cut_frames: set, claimed: np.ndarray | None = None) -> list[Comp]:
    """Push / slide transitions: the picture translates steadily in one direction for several frames and
    a different shot is in place afterwards, with no cut (the incoming shot slides in)."""
    tc = ctx.cfg["transition"]
    m, N = ctx.m, ctx.N
    tx, ty = nz(m["tx_pct"]), nz(m["ty_pct"])
    rel = ctx.motion_reliable()
    v = np.where(rel, np.hypot(tx, ty), 0.0)
    for c in cut_frames:
        v[c] = 0.0
    if claimed is not None:
        v[claimed] = 0.0              # brightness ramps (dips / flashes) fake motion
    comps = []
    for a, b in runs(v >= tc["push_motion_min_pct"]):
        if b - a + 1 < tc["slide_min_frames"] or any(a <= c <= b + 1 for c in cut_frames):
            continue
        ang = np.unwrap(np.arctan2(ty[a:b + 1], tx[a:b + 1]))
        spread = float(np.std(ang)) * 180 / math.pi
        steady = float(np.std(v[a:b + 1]) / (np.mean(v[a:b + 1]) + 1e-6))
        if spread > 20 or steady > 0.35 or ctx.same_shot(a - 1, b + 1):
            continue                   # wobbly / accelerating motion, or same shot after: a camera move
        e = b - 1                      # frame b is the last step: the incoming shot has arrived
        dx, dy = float(np.mean(tx[a:b + 1])), float(np.mean(ty[a:b + 1]))
        moving = ("left" if dx < 0 else "right") if abs(dx) >= abs(dy) else ("up" if dy < 0 else "down")
        c = Comp("push_slide", a, e, key=(a + e) // 2, score=0.85,
                 sub=f"pictures slide {moving} ({np.mean(v[a:b + 1]):.1f}% of the width per frame)")
        c.evidence = {"speed_pct_per_frame": [r1(x) for x in v[a:b + 1]], "direction": moving,
                      "motion_frames": [a, b], "easing": easing_from_steps(v[a:b + 1])}
        c.notes.append(f"the picture moves {moving} at a steady {np.mean(v[a:b + 1]):.1f}% of the width per frame "
                       f"over {ctx.fr(a, b)} and a different shot is in place by {ctx.fl(b)}")
        c.notes.append("no cut inside: the incoming shot slides in with the outgoing one (push / slide transition)")
        c.labels = {i: f"{v[i]:.1f}%/f" for i in range(max(0, a - 3), min(N, b + 4))}
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- motion effects
def detect_motion(ctx: Ctx, cut_frames: set) -> list[Comp]:
    z, w, sp, sh = ctx.cfg["zoom"], ctx.cfg["whip"], ctx.cfg["spin"], ctx.cfg["shake"]
    m, N = ctx.m, ctx.N
    rel = ctx.motion_reliable()
    for c in cut_frames:
        rel[c] = False
    ls = np.where(rel, np.log(nz(m["scale"], 1.0)), 0.0)
    rot = np.where(rel, nz(m["rot_deg"]), 0.0)
    tx, ty = nz(m["tx_pct"]), nz(m["ty_pct"])
    comps: list[Comp] = []

    # --- zooms
    thr = math.log(1 + z["min_rate"])
    zooms = []
    for sign, mask in ((1, ls >= thr), (-1, ls <= -thr)):
        for a, b in merge_close(runs(mask), 1):
            tot = float(ls[a:b + 1].sum())
            single = (a == b and abs(ls[a]) >= math.log(1 + z["instant_min"]))
            if abs(tot) < math.log(1 + z["min_total"]) and not single:
                continue
            zc = Comp("zoom_in" if sign > 0 else "zoom_out", a, b, key=a, score=0.8)
            steps = ls[a:b + 1]
            zc.evidence = {"scale_per_frame": [round(math.exp(x), 3) for x in steps],
                           "total_scale": round(math.exp(tot), 3), "easing": easing_from_steps(steps),
                           "inliers_min": r1(nz(m["motion_inliers"])[a:b + 1].min(), 2)}
            pct = (math.exp(tot) - 1) * 100
            zc.notes.append(f"scale {pct:+.0f}% over {ctx.fr(a, b)} ({b - a + 1} frame(s)); per frame: "
                            + ", ".join(f"x{math.exp(x):.3f}" for x in steps))
            zc.notes.append(f"easing: {zc.evidence['easing']} (step sizes "
                            + ", ".join(f"{abs(x) * 100:.1f}%" for x in steps) + ")")
            zc.labels = {i: f"x{math.exp(ls[i]):.2f}" for i in range(max(0, a - 3), min(N, b + 4)) if rel[i]}
            zooms.append(zc)
    used = set()
    gap = int(z["transition_gap_frames"])
    for c in sorted(cut_frames):
        before = [q for q in zooms if c - 1 - gap <= q.end <= c - 1]
        after = [q for q in zooms if c + 1 <= q.start <= c + 1 + gap]
        if not before and not after:
            continue
        zb = max(before, key=lambda q: q.end) if before else None
        za = min(after, key=lambda q: q.start) if after else None
        start = zb.start if zb else c
        end = (za.end - 1) if za else c - 1
        end = max(end, c)
        direction = "in" if ((zb and zb.type == "zoom_in") or (not zb and za and za.type == "zoom_out")) else "out"
        tc = Comp("zoom_transition", start, end, key=c, score=0.9, sub=f"zoom-{direction}", cut=c)
        tc.evidence = {"cut": c, "outgoing": zb.evidence if zb else None, "incoming": za.evidence if za else None}
        if zb:
            tc.notes.append(f"outgoing shot: {zb.notes[0]}")
        tc.notes.append(f"cut at {ctx.fl(c)}")
        if za:
            tc.notes.append(f"incoming shot: {za.notes[0]}")
            tc.notes.append(f"incoming shot is back at rest by {ctx.fl(za.end)}")
        tc.labels = {**(zb.labels if zb else {}), **(za.labels if za else {})}
        tc.labels[c] = "CUT"
        comps.append(tc)
        used.update(id(q) for q in (zb, za) if q)
    comps += [q for q in zooms if id(q) not in used]

    # --- whip pans (fast translation, usually blurred; often hides a cut)
    spd = ctx.speed(cut_frames)
    fast = spd >= w["min_speed_pct"]
    sn = nz(m["sharp_norm"])
    aniso = nz(m["grad_aniso"])
    blurdir = (np.abs(aniso) >= w["blur_aniso_min"]) & (sn < 0.5 * rmed(sn, 31)) & ~ctx.trans
    for c in cut_frames:
        blurdir[c] = False
    base_spd = np.zeros(N)
    for s0, e0 in ctx.clean_segments():
        base_spd[s0:e0 + 1] = float(np.median(spd[s0:e0 + 1]))
    # gap 2: a whip transition is split by its cut frame (no motion measurable across a cut)
    for a, b in merge_close(runs(fast | blurdir), 2):
        n_fast = int(fast[a:b + 1].sum())
        n_blur = int(blurdir[a:b + 1].sum())
        if not (n_fast >= w["min_frames"] or (n_fast >= 1 and n_blur >= 2)):
            continue
        # extend over the ease-in / ease-out frames that are still far faster than the shot's own motion
        ext = lambda i: max(w["extend_min_pct"], 5 * base_spd[i])  # noqa: E731
        while a - 1 >= 0 and spd[a - 1] >= ext(a - 1) and spd[a - 1] <= spd[a] + 0.5 and not ctx.trans[a - 1]:
            a -= 1
        while b + 1 < N and spd[b + 1] >= ext(b + 1) and spd[b + 1] <= spd[b] + 0.5 and not ctx.trans[b + 1]:
            b += 1
        cuts_in = [c for c in cut_frames if a - 1 <= c <= b + 1]
        dx = float(np.nansum(tx[a:b + 1]))
        dy = float(np.nansum(ty[a:b + 1]))
        direction = ("right" if dx < 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy < 0 else "up")
        wc = Comp("whip_pan", a, b, key=cuts_in[0] if cuts_in else a, score=0.75,
                  sub=f"camera whips {direction}" + (" (transition)" if cuts_in else ""),
                  cut=cuts_in[0] if cuts_in else None)
        wc.evidence = {"peak_speed_pct_per_frame": r1(spd[a:b + 1].max()),
                       "speed_per_frame": [r1(x) for x in spd[a:b + 1]],
                       "blur_aniso": r1(float(np.abs(aniso[a:b + 1]).max()), 2), "cuts": cuts_in}
        wc.notes.append(f"picture moves up to {r1(spd[a:b + 1].max())}% of frame width per frame over {ctx.fr(a, b)}")
        if blurdir[a:b + 1].any():
            wc.notes.append("strong directional blur (edges smeared along the motion)")
        if cuts_in:
            wc.notes.append(f"cut hidden inside the whip at {ctx.fl(cuts_in[0])}")
        wc.labels = {i: f"{spd[i]:.0f}%/f" for i in range(max(0, a - 3), min(N, b + 4))}
        comps.append(wc)

    # --- spins
    for a, b in merge_close(runs(np.abs(rot) >= sp["min_rate_deg"]), 1):
        tot = float(rot[a:b + 1].sum())
        if abs(tot) < sp["min_total_deg"]:
            continue
        sc = Comp("spin", a, b, key=a, score=0.8, sub="clockwise" if tot > 0 else "counter-clockwise")
        sc.evidence = {"total_deg": r1(tot), "deg_per_frame": [r1(x) for x in rot[a:b + 1]],
                       "easing": easing_from_steps(rot[a:b + 1])}
        sc.notes.append(f"rotation {tot:+.0f} deg over {ctx.fr(a, b)}; per frame: "
                        + ", ".join(f"{x:+.1f}" for x in rot[a:b + 1]))
        sc.labels = {i: f"{rot[i]:+.0f}deg" for i in range(max(0, a - 3), min(N, b + 4))}
        comps.append(sc)

    # --- shake: high-frequency jitter of the frame position inside one shot
    win = int(sh["window"])
    for s0, e0 in ctx.clean_segments(2 * win):
        s1 = e0 + 1
        x = tx[s0:s1].copy()
        y = ty[s0:s1].copy()
        r = rel[s0:s1]
        x[~r], y[~r] = 0.0, 0.0
        hx = x - uniform_filter1d(x, 7, mode="nearest")
        hy = y - uniform_filter1d(y, 7, mode="nearest")
        en = np.sqrt(np.maximum(uniform_filter1d(hx * hx + hy * hy, win, mode="nearest"), 0.0))
        sgn = np.sign(np.where(np.abs(hx) > np.abs(hy), hx, hy))
        flips = np.abs(np.diff(sgn, prepend=sgn[0])) > 0
        flips_w = uniform_filter1d(flips.astype(float), win, mode="nearest") * win
        mask = (en >= sh["min_amp_pct"]) & (flips_w >= sh["min_sign_changes"])
        mag = np.hypot(hx, hy)
        for a, b in merge_close(runs(mask), 2):
            # the window smoothing smears the run: trim to frames that really jump
            while a < b and mag[a] < 0.5 * sh["min_amp_pct"]:
                a += 1
            while b > a and mag[b] < 0.5 * sh["min_amp_pct"]:
                b -= 1
            if b - a + 1 < sh["min_frames"]:
                continue
            # a shake oscillates: the direction must flip repeatedly INSIDE the run (a single jump does not)
            if int(flips[a + 1:b + 1].sum()) < sh["min_sign_changes"]:
                continue
            A_, B_ = s0 + a, s0 + b
            kc = Comp("shake", A_, B_, key=A_, score=0.6)
            kc.evidence = {"rms_jitter_pct": r1(float(en[a:b + 1].max()), 2),
                           "direction_flips": int(flips[a:b + 1].sum())}
            kc.notes.append(f"frame position jitters by up to {kc.evidence['rms_jitter_pct']}% of the frame "
                            f"with {kc.evidence['direction_flips']} direction changes over {ctx.fr(A_, B_)}")
            kc.labels = {i: f"{tx[i]:+.1f},{ty[i]:+.1f}" for i in range(max(0, A_ - 3), min(N, B_ + 4))}
            comps.append(kc)
    return comps


# ----------------------------------------------------------------------------- freeze / stutter / repeats
def detect_repeats(ctx: Ctx) -> list[Comp]:
    fz, st = ctx.cfg["freeze"], ctx.cfg["stutter"]
    m, N = ctx.m, ctx.N
    dup = nz(m["dup"]) > 0.5
    fill = nz(m["proxy_fill"]) > 0.5
    dark = nz(m["luma_mean"]) < 3
    comps = []
    long_runs = set()
    for a, b in runs(dup & ~fill & ~dark):
        if b - a + 1 >= fz["min_frames"] - 1:
            s, e = a - 1, b
            c = Comp("freeze", s, e, key=s, score=0.9)
            shot_still = s <= 1 or e >= N - 2
            c.evidence = {"held_frames": e - s + 1, "max_frame_diff": r1(nz(m["frame_diff"])[a:b + 1].max(), 3),
                          "motion_before": r1(med(nz(m["frame_diff"]), s - 6, s - 1), 2),
                          "motion_after": r1(med(nz(m["frame_diff"]), e + 1, e + 6), 2)}
            c.notes.append(f"{ctx.fl(s)} is held for {e - s + 1} frames (until {ctx.fl(e)}): "
                           f"frame-to-frame change {c.evidence['max_frame_diff']} (normal motion "
                           f"{c.evidence['motion_before']} before / {c.evidence['motion_after']} after)")
            if shot_still:
                c.sub = "still image?"
            c.labels = {i: ("HOLD" if s <= i <= e else "") for i in range(max(0, s - 3), min(N, e + 4))}
            comps.append(c)
            long_runs.update(range(s, e + 1))

    rk = nz(m["rep_k"]).astype(int)
    re_ = nz(m["rep_err"], 1e9)
    ep = nz(m["err_prev"], 0)
    rep = (rk >= 2) & (re_ <= st["rep_err_max"]) & (re_ <= st["rep_ratio_max"] * ep) & ~dup
    for a, b in merge_close(runs(rep), 1):
        idx = [t for t in range(a, b + 1) if rep[t]]
        if len(idx) < st["min_repeats"]:
            continue
        s = min(t - rk[t] for t in idx)
        e = b
        ks = [int(rk[t]) for t in idx]
        k_mode = max(set(ks), key=ks.count)
        pattern = (f"loop of {k_mode} frames repeated {round((e - s + 1) / k_mode)}x" if ks.count(k_mode) >= 0.8 * len(ks)
                   else "back-and-forth (boomerang) pattern: " + ",".join(map(str, ks)))
        c = Comp("stutter", s, e, key=s, score=0.85, sub=pattern)
        c.evidence = {"repeat_distance_frames": ks, "match_error_max": r1(re_[idx].max(), 2),
                      "normal_frame_change": r1(med(ep, s - 6, s - 1), 2)}
        c.notes.append(f"{ctx.fr(s, e)}: {pattern}; frames {ctx.fl(idx[0])}.. repeat earlier frames exactly "
                       f"(match error {c.evidence['match_error_max']} vs normal change {c.evidence['normal_frame_change']})")
        c.labels = {t: (f"={t - rk[t]}" if rep[t] else "") for t in range(max(0, s - 3), min(N, e + 4))}
        comps.append(c)

    # stepped frame repeat (every 2nd/3rd frame duplicated) outside freezes
    W = 12
    dd = (dup & ~fill & ~dark).astype(float)
    dens = uniform_filter1d(dd, W, mode="nearest")
    stepped = (dens >= 0.3) & (dens <= 0.75)
    for t in long_runs:
        stepped[t] = False
    for a, b in merge_close(runs(stepped), 2):
        if b - a + 1 < W:
            continue
        # the density window blurs the edges: snap to the first / last duplicated frame
        dl_ = [t for t in range(max(1, a - W // 2), min(N, b + W // 2 + 1)) if dd[t] > 0 and t not in long_runs]
        if dl_:
            a, b = dl_[0] - 1, dl_[-1]
        frac = float(dd[a + 1:b + 1].mean())
        c = Comp("frame_repeat", a, b, key=a, score=0.6,
                 sub=f"about every {round(1 / max(1e-6, 1 - frac))}th frame is new (on {round(1 / max(1e-6, 1 - frac))}s)")
        c.evidence = {"duplicate_fraction": r1(frac, 2)}
        c.notes.append(f"{frac:.0%} of frames in {ctx.fr(a, b)} are duplicates of the previous frame (stepped / "
                       f"low-frame-rate look)")
        comps.append(c)

    # strobe: luma alternating hard frame to frame
    L = nz(m["luma_mean"])
    dl = np.diff(L, prepend=L[0])
    # a swing counts when it is large relative to the brighter of the two frames (dark content strobes too)
    big = np.abs(dl) >= np.maximum(st["strobe_min_delta"], st["strobe_rel"] * np.maximum(L, np.roll(L, 1)))
    alt = big & (np.sign(dl) != np.sign(np.roll(dl, 1)))
    for a, b in merge_close(runs(alt), 1):
        if b - a + 1 < 4:
            continue
        # frames a..b-1 are strobed; frame b is the swing back to normal
        e = b - 1
        c = Comp("strobe", a, e, key=a, score=0.8, sub=f"{(e - a + 2) // 2} pulses")
        c.evidence = {"luma_swings_pct": [r1(x) for x in dl[a:b + 1]], "luma_pct": [r1(x) for x in L[a:b + 1]]}
        c.notes.append(f"brightness flips every frame over {ctx.fr(a, e)}: "
                       + ", ".join(f"{L[i]:.0f}%" for i in range(a, b + 1)))
        c.labels = {i: f"L{L[i]:.0f}%" for i in range(max(0, a - 4), min(N, b + 4))}
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- rgb split / glitch
def detect_rgb_glitch(ctx: Ctx, cut_frames: set) -> list[Comp]:
    rc, gc = ctx.cfg["rgb"], ctx.cfg["glitch"]
    m, N = ctx.m, ctx.N
    sh = nz(m["rgb_shift_px"])
    gain = nz(m["rgb_resp"])
    lstd = nz(m["luma_std"])
    mask = (sh >= rc["min_shift_px"]) & (gain >= rc["min_gain"]) & (lstd >= rc["min_luma_std"])
    comps = []
    for a, b in merge_close(runs(mask), 1):
        k = a + int(np.argmax(sh[a:b + 1]))
        c = Comp("rgb_split", a, b, key=a, score=0.85)
        rx, bx = nz(m["rgb_r_dx"]), nz(m["rgb_b_dx"])
        ry, by = nz(m["rgb_r_dy"]), nz(m["rgb_b_dy"])
        c.evidence = {"max_shift_src_px": r1(sh[k]), "red_offset_px": [r1(rx[k]), r1(ry[k])],
                      "blue_offset_px": [r1(bx[k]), r1(by[k])],
                      "shift_per_frame_px": [r1(x) for x in sh[a:b + 1]], "edge_match_gain": r1(gain[k], 2)}
        def side(dx, dy):
            if abs(dx) < 0.5 and abs(dy) < 0.5:
                return "aligned"
            return f"{abs(dx):.0f}px {'left' if dx < 0 else 'right'}" if abs(dx) >= abs(dy) else \
                f"{abs(dy):.0f}px {'up' if dy < 0 else 'down'}"
        c.notes.append(f"colour channels misaligned over {ctx.fr(a, b)}: red {side(rx[k], ry[k])}, "
                       f"blue {side(bx[k], by[k])} of green (source pixels, max at {ctx.fl(k)})")
        if len(set(round(x) for x in sh[a:b + 1])) > 1:
            c.notes.append("offset per frame: " + ", ".join(f"{x:.0f}px" for x in sh[a:b + 1]))
        c.labels = {i: f"{sh[i]:.0f}px" for i in range(max(0, a - 3), min(N, b + 4))}
        comps.append(c)

    bd = nz(m["band_dev_pct"])
    tear = nz(m["row_tear"])
    bands_base = rmed(bd, 61)
    tear_base = rmed(tear, 61)
    # a real slice glitch displaces picture content, so the frame also stops matching the previous one;
    # band/tear spikes without that drop are aliasing on periodic textures (grids, fences, tiles)
    corr = nz(m["corr_prev"], 1.0)
    corr_drop = rmed(corr, 31) - corr >= gc["corr_drop_min"]
    gl = (((bd >= gc["band_dev_min_pct"]) & (bd >= gc["rel_min"] * (bands_base + 0.3))) |
          ((tear >= gc["row_tear_min"]) & (tear >= gc["rel_min"] * (tear_base + 0.5)))) & corr_drop
    for c_ in cut_frames:
        gl[max(0, c_ - 1):c_ + 2] = False
    gl &= ~ctx.trans & (lstd >= rc["min_luma_std"])
    for t in ctx.layout_changes:
        gl[max(0, t - 1):t + 2] = False
    # a held glitch shows up twice: when the bands jump away and when they jump back; pair them
    for a, b in merge_close(runs(gl), int(gc["max_frames"])):
        if b - a + 1 > gc["max_frames"] + 1:
            continue
        if b > a and ctx.seg_id[a] == ctx.seg_id[b] and ctx.corr(a - 1, b) >= 0.9:
            b -= 1                      # frame b is the picture snapping back
        c = Comp("glitch", a, b, key=a, score=0.55)
        c.evidence = {"band_shift_spread_pct": r1(bd[a:b + 1].max()), "row_tear": r1(tear[a:b + 1].max())}
        c.notes.append(f"horizontal bands of the picture move differently / tear over {ctx.fr(a, b)} "
                       f"(band spread {c.evidence['band_shift_spread_pct']}% of width, tear {c.evidence['row_tear']})")
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- blur
def detect_blur(ctx: Ctx, cut_frames: set) -> list[Comp]:
    bc = ctx.cfg["blur"]
    m, N = ctx.m, ctx.N
    raw = nz(m["crisp"] if "crisp" in m else m["sharp_norm"], NAN)
    L = nz(m["luma_mean"])
    spd = ctx.speed(cut_frames)
    # upper envelope (max of t-1, t, t+1 inside the shot): fine patterns / pixel art can alternate
    # crisp-soft-crisp every frame (aliasing); a real blur stays soft for consecutive frames
    sn = raw.copy()
    for s0, e0 in ctx.clean_segments():
        seg = raw[s0:e0 + 1]
        for i in range(len(seg)):
            w_ = seg[max(0, i - 1):i + 2]
            w_ = w_[np.isfinite(w_)]
            sn[s0 + i] = float(w_.max()) if len(w_) else NAN
    # a blurred frame must be much softer than the sharp frames BEFORE it and AFTER it in the same shot
    # (where both exist). A permanent change in detail - e.g. a text overlay appearing - is not a blur.
    ref = np.full(N, NAN)
    low = np.zeros(N, bool)
    W = int(bc["reference_frames"])
    for s0, e0 in ctx.clean_segments():
        for t in range(s0, e0 + 1):
            if L[t] <= 5 or not np.isfinite(sn[t]):
                continue
            sides = []
            video_edge = False
            for lo_, hi_, at_edge in ((max(s0, t - W), t - 3, s0 == 0), (t + 3, min(e0, t + W), e0 == N - 1)):
                seg = sn[lo_:hi_ + 1] if hi_ >= lo_ else np.zeros(0)
                seg = seg[np.isfinite(seg)]
                if len(seg) >= 3:
                    sides.append(float(np.percentile(seg, 80)))
                elif at_edge:
                    video_edge = True        # this side is missing because the video starts / ends here
            if len(sides) == 1 and video_edge:
                sides = []                   # one-sided at the video start / end: content drift, not an edit
            if sides:
                ref[t] = max(sides)
                low[t] = all(sn[t] <= bc["ratio_max"] * v for v in sides)
    # the envelope trims one frame at each end of a blur: give those frames back using the raw value
    for a_, b_ in runs(low):
        for t in (a_ - 1, b_ + 1):
            if 0 <= t < N and np.isfinite(ref[t]) and np.isfinite(raw[t]) and raw[t] <= bc["ratio_max"] * ref[t]:
                low[t] = True
    ratio = raw / (ref + 1e-9)
    low &= ~ctx.trans
    comps = []
    for a, b in runs(low):
        if b - a + 1 < bc["min_frames"]:
            continue
        motion = float(np.nanmax(spd[a:b + 1])) if b >= a else 0.0
        c = Comp("blur", a, b, key=a, score=0.6)
        rr = ratio[a:b + 1]
        k = a + int(np.nanargmin(rr))
        shape = []
        if k > a:
            shape.append("blur in")
        if k < b:
            shape.append("blur out")
        c.sub = " + ".join(shape) or "blurred"
        if motion >= bc["max_motion_pct"]:
            c.sub += " (motion blur)"
        c.evidence = {"sharpness_ratio_min": r1(float(np.nanmin(rr)), 2), "sharpness_ratio": [r1(x, 2) for x in rr],
                      "max_motion_pct": r1(motion)}
        c.notes.append(f"detail drops to {np.nanmin(rr):.0%} of the shot's normal sharpness at {ctx.fl(k)} "
                       f"({ctx.fr(a, b)})" + (" while the picture moves fast" if motion >= bc["max_motion_pct"] else ""))
        c.labels = {i: f"S{100 * ratio[i]:.0f}%" for i in range(max(0, a - 3), min(N, b + 4)) if np.isfinite(ratio[i])}
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- colour / light leak
def detect_color(ctx: Ctx, cut_frames: set) -> list[Comp]:
    cc, lc = ctx.cfg["color"], ctx.cfg["light_leak"]
    m, N = ctx.m, ctx.N
    comps = []
    corr = m["corr_prev"]
    ok = (ctx.tstd >= 4) & (np.roll(ctx.tstd, 1) >= 4)
    inv = np.where(ok, nz(corr, 1) <= cc["invert_corr_max"], False)
    for t in np.where(inv)[0]:
        if t == 0 or ctx.inverted(t - 1, t) < cc["invert_match_min"]:
            inv[t] = False
    idx = list(np.where(inv)[0])
    i = 0
    while i < len(idx):
        a = int(idx[i])
        b_ = next((int(j) - 1 for j in idx[i + 1:] if j - a <= 120), None)
        e = b_ if b_ is not None else a
        c = Comp("invert", a, e, key=a, score=0.75)
        c.notes.append(f"picture becomes the negative of the previous frame at {ctx.fl(a)} "
                       f"(correlation {r1(corr[a], 2)})" + (f", back to normal at {ctx.fl(e + 1)}" if b_ else ""))
        comps.append(c)
        i += 2 if b_ is not None else 1

    S = nz(m["sat_mean"])
    L = nz(m["luma_mean"])
    h = int(cc["sat_hold_frames"])
    for s0, e0 in ctx.clean_segments(2 * h):
        t = s0 + h
        while t <= e0 - h + 1:
            before, after = med(S, t - h, t - 1), med(S, t, t + h - 1)
            step = after - before
            if abs(step) >= cc["sat_step_min"] and ok[t] and nz(corr, 1)[t] > 0.8:
                # the step frame = largest single-frame saturation change in the window
                k = t - h + int(np.argmax(np.abs(np.diff(S[t - h:t + h])))) + 1
                # a step change lives on one frame: the first frame with the new saturation
                c = Comp("sat_pop", k, k, key=k, score=0.6,
                         sub="saturation up" if step > 0 else "saturation down")
                c.evidence = {"sat_before_pct": r1(before), "sat_after_pct": r1(after)}
                c.notes.append(f"saturation {r1(before)}% -> {r1(after)}% at {ctx.fl(k)} with the same picture")
                comps.append(c)
                t += 2 * h
            else:
                t += 1

    # light leak: warm, soft, brightening overlay that comes and goes without a cut
    A, B, LF = nz(m["lab_a"]), nz(m["lab_b"]), nz(m["lowfreq"])
    base_L, base_w, base_lf = rmed(L, 61), rmed(A + B, 61), rmed(LF, 61)
    leak = ((L - base_L) >= lc["luma_rise_min"]) & (((A + B) - base_w) >= lc["warm_rise_min"]) & \
           ((LF - base_lf) >= lc["lowfreq_rise_min"])
    rise_l, rise_w = L - base_L, (A + B) - base_w
    for a, b in merge_close(runs(leak), 2):
        if b - a + 1 < lc["min_frames"]:
            continue
        pk_l = float(rise_l[a:b + 1].max())
        # leaks fade in / out softly: follow the brightening down to a few % of its peak, as long as it
        # keeps falling away from the peak (stops at noise or at a different change)
        floor = max(lc["tail_min_pct"], lc["tail_rel"] * pk_l)
        tail = lambda i, j: (rise_l[i] >= floor and rise_w[i] >= 0 and rise_l[i] <= rise_l[j] + 0.3  # noqa: E731
                             and not ctx.trans[i])
        while a - 1 >= 0 and tail(a - 1, a):
            a -= 1
        while b + 1 < N and tail(b + 1, b):
            b += 1
        c = Comp("light_leak", a, b, key=a, score=0.5)
        c.evidence = {"luma_rise_pct": r1(float((L - base_L)[a:b + 1].max())),
                      "warmth_rise": r1(float(((A + B) - base_w)[a:b + 1].max())),
                      "soft_gradient_rise": r1(float((LF - base_lf)[a:b + 1].max()))}
        c.notes.append(f"warm, soft brightening over {ctx.fr(a, b)}: luma +{c.evidence['luma_rise_pct']}%, "
                       f"warmth +{c.evidence['warmth_rise']}, large-scale gradient +{c.evidence['soft_gradient_rise']}")
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- split / mirror / text
def detect_layout(ctx: Ctx, cut_frames: set) -> list[Comp]:
    sc, tc = ctx.cfg["split_mirror"], ctx.cfg["text"]
    m = ctx.m
    comps = []
    flow = nz(m["flow_mag_pct"])
    for key, typ, label_ in (("sym_lr", "mirror", "left/right mirror"), ("sym_tb", "mirror", "top/bottom mirror"),
                             ("tile", "multi_screen", "repeated tiles")):
        thr = sc["sym_min"] if typ == "mirror" else sc["tile_min"]
        v = nz(m[key])
        for a, b in merge_close(runs(v >= thr), 2):
            if b - a + 1 < sc["min_frames"]:
                continue
            if float(np.median(flow[a:b + 1])) < sc["min_motion_pct"]:
                continue                 # static graphics / test patterns: not an effect we can confirm
            c = Comp(typ, a, b, key=a, score=0.6, sub=label_)
            c.evidence = {key: r1(float(np.median(v[a:b + 1])), 2)}
            c.notes.append(f"{label_}: similarity {c.evidence[key]} held over {ctx.fr(a, b)}")
            comps.append(c)
    for key, pos, typ_sub in (("seam_v", "seam_v_pos", "vertical split"), ("seam_h", "seam_h_pos", "horizontal split")):
        v = nz(m[key])
        p = nz(m[pos])
        for a, b in merge_close(runs(v >= sc["seam_min"]), 2):
            if b - a + 1 < sc["min_frames"]:
                continue
            if float(np.std(p[a:b + 1])) > 0.01:
                continue                 # a moving edge is a wipe, not a split
            if float(np.median(flow[a:b + 1])) < sc["min_motion_pct"]:
                continue
            c = Comp("split_screen", a, b, key=a, score=0.55, sub=f"{typ_sub} at {np.median(p[a:b + 1]):.0%}")
            c.notes.append(f"straight full-length edge at {np.median(p[a:b + 1]):.0%} of the frame held over {ctx.fr(a, b)}")
            comps.append(c)
    ts = nz(m["text_score"])
    found = []
    for s0, e0 in ctx.clean_segments(tc["min_frames"] + 6):
        t = s0 + 3                          # text present from the first frame of a shot is ambiguous
        while t <= e0 - 2:
            before, after = med(ts, max(s0, t - 6), t - 1), med(ts, t, min(e0, t + 5))
            if after >= tc["score_min"] and after - before >= max(tc["rise_min"], tc["rise_rel"] * before):
                level = before + 0.5 * (after - before)
                a = t
                while a - 1 > s0 and ts[a - 1] >= level:
                    a -= 1
                b = a
                while b + 1 <= e0 and ts[b + 1] >= level:
                    b += 1
                if b - a + 1 >= tc["min_frames"]:
                    found.append((a, b))
                t = max(t + 1, b + 1)             # always advance (the run may end before t)
            else:
                t += 1
    for a, b in found:
        c = Comp("text", a, b, key=a, score=0.45)
        c.evidence = {"text_area_pct": r1(100 * float(ts[a:b + 1].max()), 2)}
        c.notes.append(f"text-like high-contrast shapes appear at {ctx.fl(a)} covering up to "
                       f"{c.evidence['text_area_pct']}% of the frame (until {ctx.fl(b)})")
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- speed ramp
def detect_speed(ctx: Ctx, cut_frames: set, claimed: np.ndarray) -> list[Comp]:
    sr = ctx.cfg["speed_ramp"]
    m, N = ctx.m, ctx.N
    # only frames whose motion was actually tracked count; untrackable (flat) frames are unknown, not "still"
    src = nz(m.get("motion_src", np.ones(N)), 1)
    ok = (src == 1) & (nz(m["motion_pts"]) >= ctx.cfg["zoom"]["min_pts"]) & np.isfinite(m["flow_mag_pct"])
    v_raw = np.where(ok, nz(m["flow_mag_pct"]), np.nan)
    v = np.full(N, np.nan)
    sm = int(sr["smooth"])
    for i in range(N):
        w_ = v_raw[max(0, i - sm // 2):i + sm // 2 + 1]
        if np.isfinite(w_).sum() >= max(2, sm // 2):
            v[i] = float(np.nanmean(w_))
    comps = []
    h = 8
    for s0, e0 in ctx.clean_segments(2 * h + 1):
        s1 = e0 + 1
        t = s0 + h
        while t < s1 - h:
            pre, post = med(v, t - h, t - 1), med(v, t, t + h - 1)
            cover = min(np.isfinite(v[t - h:t]).mean(), np.isfinite(v[t:t + h]).mean())
            if not (np.isfinite(pre) and np.isfinite(post)) or cover < 0.7:
                t += 1
                continue
            hi_, lo_ = max(pre, post), min(pre, post)
            if hi_ >= sr["min_speed_pct"] and hi_ >= sr["min_ratio"] * max(lo_, 0.02) and not claimed[t - h:t + h].any():
                a, b = t - h // 2, t + h // 2
                c = Comp("speed_ramp", a, b, key=t, score=0.4, sub="slows down" if post < pre else "speeds up")
                c.evidence = {"motion_before_pct": r1(pre, 2), "motion_after_pct": r1(post, 2),
                              "ratio": r1(hi_ / max(lo_, 0.02))}
                c.notes.append(f"picture motion changes {r1(pre, 2)}% -> {r1(post, 2)}% of width per frame around "
                               f"{ctx.fl(t)} inside one shot (x{c.evidence['ratio']})")
                comps.append(c)
                t += 2 * h
            else:
                t += 1
    return comps


# ----------------------------------------------------------------------------- unknown anomalies
def surprise(ctx: Ctx) -> tuple[np.ndarray, np.ndarray]:
    """Per frame: how far luma / saturation / colour / picture change jump above their local normal (robust z),
    and which of the four signals jumped most."""
    m, N = ctx.m, ctx.N
    feats = {
        "luma change": np.abs(np.diff(nz(m["luma_mean"]), prepend=0)),
        "saturation change": np.abs(np.diff(nz(m["sat_mean"]), prepend=0)),
        "colour change": np.hypot(np.diff(nz(m["lab_a"]), prepend=0), np.diff(nz(m["lab_b"]), prepend=0)),
        "picture change": nz(m["frame_diff"]),
    }
    z = np.zeros(N)
    which = np.empty(N, dtype=object)
    for name, f in feats.items():
        base = rmed(f, 61)
        mad = rmed(np.abs(f - base), 61) * 1.4826 + 0.5
        zz = (f - base) / mad
        upd = zz > z
        which[upd] = name
        z = np.maximum(z, zz)
    return z, which


def near_misses(ctx: Ctx, events: list[dict], cut_frames: list[int]) -> list[dict]:
    """Possible misses for the user (and the reviewer) to check: the strongest sudden changes that no event and no
    cut explains - local peaks of the surprise score from near_miss.z_min up, at least spacing_frames apart.
    Evidence only: nothing here becomes an event."""
    nc = ctx.cfg.get("near_miss", {})
    z, which = surprise(ctx)
    N, pad = ctx.N, int(nc.get("pad_frames", 3))
    covered = np.zeros(N, bool)
    covered[:2] = True
    for ev in events:
        covered[max(0, ev["start"] - pad):min(N, ev["end"] + pad + 1)] = True
    for c in cut_frames:
        covered[max(0, c - 2):min(N, c + 3)] = True
    peaks = [k for k in range(1, N - 1) if not covered[k] and z[k] >= nc.get("z_min", 5.0)
             and z[k] >= z[k - 1] and z[k] >= z[k + 1]]
    out = []
    for k in sorted(peaks, key=lambda k: -z[k]):
        if len(out) >= int(nc.get("max_items", 12)):
            break
        if all(abs(k - o["frame"]) >= int(nc.get("spacing_frames", 12)) for o in out):
            out.append({"frame": int(k), "tc": frame_to_tc(int(k), ctx.fps, ctx.drop), "signal": str(which[k]),
                        "z": r1(z[k]),
                        "why": f"sudden {which[k]} ({r1(z[k])}x the usual variation) that no event or cut explains"})
    return sorted(out, key=lambda o: o["frame"])


def detect_unknown(ctx: Ctx, cut_frames: set, claimed: np.ndarray) -> list[Comp]:
    uc = ctx.cfg["unknown"]
    N = ctx.N
    z, which = surprise(ctx)
    mask = (z >= uc["z_min"]) & ~claimed & ~ctx.trans
    for c in cut_frames:
        mask[max(0, c - 1):c + 2] = False
    mask[:2] = False
    comps = []
    for a, b in merge_close(runs(mask), 1):
        if b - a + 1 > uc["max_frames"]:
            continue
        k = a + int(np.argmax(z[a:b + 1]))
        c = Comp("unknown", a, b, key=k, score=0.3, sub=str(which[k]))
        c.evidence = {"strongest_signal": str(which[k]), "robust_z": r1(z[k])}
        c.notes.append(f"unexplained spike in {which[k]} ({r1(z[k])}x the usual variation) at {ctx.fl(k)}; "
                       f"no known effect pattern matched")
        comps.append(c)
    return comps


# ----------------------------------------------------------------------------- assembly
LONG_TYPES = {"split_screen", "mirror", "multi_screen", "text", "frame_repeat", "light_leak"}
CUT_OWNERS = {"flash_white", "flash", "flash_black", "dip_black", "dip_white", "fade_in", "fade_out",
              "zoom_transition", "whip_pan", "spin", "blur", "crossfade", "wipe", "mask_reveal", "luma_fade",
              "push_slide", "glitch", "strobe"}


def assemble(ctx: Ctx, comps: list[Comp], cuts: list[dict], jumps: list[dict]):
    ec = ctx.cfg["events"]
    cut_frames = sorted(c["frame"] for c in cuts)
    owned = {}
    for c in cut_frames:
        for comp in comps:
            # only transitions can contain / hide a cut; an overlay effect next to a cut leaves it a plain cut
            if comp.type not in CUT_OWNERS:
                continue
            if comp.start - 1 <= c <= comp.end + 1:
                owned.setdefault(c, []).append(comp)
    # merge components into events
    comps = sorted(comps, key=lambda q: (q.start, q.end))
    groups: list[list[Comp]] = []
    for q in comps:
        long_q = q.type in LONG_TYPES or (q.end - q.start + 1) > ec["max_merge_frames"]
        placed = False
        if not long_q:
            for g in groups[::-1]:
                g_long = any(x.type in LONG_TYPES or (x.end - x.start + 1) > ec["max_merge_frames"] for x in g)
                if g_long:
                    continue
                gs, ge = min(x.start for x in g), max(x.end for x in g)
                if q.start <= ge + ec["merge_gap_frames"] and q.end >= gs - ec["merge_gap_frames"]:
                    g.append(q)
                    placed = True
                    break
        if not placed:
            groups.append([q])
    events = []
    pri = {t: i for i, t in enumerate(taxonomy.PRIORITY)}
    for g in sorted(groups, key=lambda g: min(x.start for x in g)):
        prim = min(g, key=lambda x: (pri.get(x.type, 99), -x.score))
        s, e = min(x.start for x in g), max(x.end for x in g)
        comp_cuts = {x.cut for x in g if x.cut is not None}
        cuts_in = sorted(comp_cuts) if comp_cuts else sorted(
            c for c in cut_frames if s - 1 <= c <= e + 1 and any(x in g for x in owned.get(c, [])))
        labels = {}
        for x in sorted(g, key=lambda x: -pri.get(x.type, 99)):
            labels.update(x.labels)
        types = []
        for x in sorted(g, key=lambda x: pri.get(x.type, 99)):
            if x.type not in types:
                types.append(x.type)
        events.append({
            "type": prim.type, "type_label": taxonomy.label(prim.type), "family": taxonomy.family(prim.type),
            "sub": prim.sub, "types": types, "start": int(s), "end": int(e), "key": int(prim.key),
            "duration_frames": int(e - s + 1), "cuts": [int(c) for c in cuts_in],
            "score": round(max(x.score for x in g), 2),
            "components": [x.as_dict() for x in sorted(g, key=lambda x: pri.get(x.type, 99))],
            "labels": {int(k): v for k, v in labels.items()},
        })
    for i, ev in enumerate(events, 1):
        ev["id"] = f"E{i:03d}"
    plain = []
    for c in cuts:
        f = c["frame"]
        if f in owned:
            continue
        plain.append({**c, "type": "hard_cut"})
    for j in jumps:
        if not any(ev["start"] - 1 <= j["frame"] <= ev["end"] + 1 for ev in events):
            plain.append({**j, "type": "jump_cut"})
    plain.sort(key=lambda c: c["frame"])
    return events, plain


SHOT_TRANSITIONS = ("crossfade", "wipe", "mask_reveal", "luma_fade", "push_slide")


def shots_from(N: int, plain_cuts: list[dict], events: list[dict]) -> list[dict]:
    """Shot list: split at plain cuts, at cuts owned by effects, and at the middle of gradual transitions."""
    bounds = {c["frame"] for c in plain_cuts if c.get("type") == "hard_cut"}
    for ev in events:
        for comp in ev["components"]:
            if comp.get("cut") is not None:
                bounds.add(comp["cut"])
            if comp["type"] in SHOT_TRANSITIONS or "transition" in (comp.get("sub") or ""):
                if comp.get("cut") is None:
                    bounds.add((comp["start"] + comp["end"] + 1) // 2)
    b = sorted(x for x in bounds if 0 < x < N)
    edges = [0] + b + [N]
    return [{"index": i + 1, "start": s, "end": e - 1, "frames": e - s}
            for i, (s, e) in enumerate(zip(edges[:-1], edges[1:]))]


def run_detection(ctx: Ctx):
    N = ctx.N
    cuts, jumps = detect_cuts(ctx)
    cut_frames = {c["frame"] for c in cuts}
    comps: list[Comp] = []
    comps += detect_flashes(ctx)
    comps += detect_dips(ctx)
    lum_claimed = np.zeros(N, bool)
    for q in comps:
        lum_claimed[max(0, q.start - 1):q.end + 2] = True
    comps += detect_slides(ctx, cut_frames, lum_claimed)
    claimed = np.zeros(N, bool)
    for q in comps:
        claimed[max(0, q.start - 1):q.end + 2] = True
    for t in ctx.layout_changes:
        claimed[max(0, t - 1):t + 2] = True
    comps += detect_gradual(ctx, cut_frames, claimed)

    # shot segmentation: transitions (flash / dip / gradual) become their own segments
    trans = np.zeros(N, bool)
    bounds = set()
    for q in comps:
        trans[q.start:q.end + 1] = True
        bounds.update((q.start, q.end + 1))
        if q.cut is not None:
            bounds.add(q.cut)
    hard = {c for c in cut_frames if not trans[c] and not trans[c - 1]}
    bounds |= hard
    ctx.set_segments(bounds, trans)

    comps += detect_motion(ctx, hard)
    comps += detect_repeats(ctx)
    comps += detect_rgb_glitch(ctx, cut_frames)
    comps += detect_blur(ctx, hard)
    comps += detect_color(ctx, hard)
    comps += detect_layout(ctx, hard)
    claimed = np.zeros(N, bool)
    for q in comps:
        claimed[max(0, q.start - 1):q.end + 2] = True
    comps += detect_speed(ctx, hard, claimed)
    for q in comps:
        claimed[max(0, q.start - 1):q.end + 2] = True
    comps += detect_unknown(ctx, cut_frames, claimed)
    inverts = [q for q in comps if q.type == "invert"]
    comps = [q for q in comps if not (q.type == "flash_color" and any(
        min(q.end, v.end) - max(q.start, v.start) + 1 >= 0.5 * (q.end - q.start + 1) for v in inverts))]
    # drop shakes / speed ramps / blur that are only side effects of freezes and stutters
    hold = np.zeros(ctx.N, bool)
    for q in comps:
        if q.type in ("freeze", "stutter"):
            hold[max(0, q.start - 1):q.end + 2] = True
    comps = [q for q in comps if not (q.type in ("shake", "speed_ramp", "unknown") and hold[q.start:q.end + 1].mean() > 0.3)]
    events, plain = assemble(ctx, comps, cuts, jumps)
    return events, plain, shots_from(ctx.N, plain, events)
