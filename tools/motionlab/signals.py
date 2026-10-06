"""Per-frame signal pass.

Every frame is decoded once by ffmpeg (downscaled, piped as raw BGR) so frame N here is exactly
frame N in every later ffmpeg extraction. Metrics per frame (index t compares frame t with t-1):

  cut_hist      HSV histogram Bhattacharyya distance to previous frame (0..1)
  frame_diff    mean |gray(t) - gray(t-1)| (0..255)
  corr_prev     correlation of 96px thumbnails with previous frame (-1..1, brightness invariant)
  corr_skip     same, with frame t-2 (finds single inserted frames)
  luma_*        BT.709 luma mean/std/p05/p95 in %
  sat_mean      HSV saturation mean in %
  lab_a, lab_b  mean CIELab a*/b* (tint: +a red, -a green, +b yellow, -b blue)
  sharpness     Laplacian variance; sharp_norm = sharpness / luma variance (contrast invariant);
                sharp_med = median of that over a 4x3 grid (immune to local overlays such as text);
                crisp = Laplacian / gradient energy on the strongest edges (edge sharpness, used for blur)
  grad_aniso    log(|Gx|/|Gy|): strongly +/- under directional (motion) blur
  dup           1 if frame is a duplicate of the previous one
  rep_k/rep_err best match among frames t-2..t-K (stutter/loop detection); err_prev = thumb diff to t-1
  tx/ty_pct     global motion of the frame centre, % of width/height per frame (LK + RANSAC similarity)
  scale, rot_deg  per-frame zoom factor and rotation; motion_inliers, motion_pts = fit quality
  flow_mag_pct  median feature motion, % of width; warp_resid = residual after motion compensation
  pc_*          phase-correlation translation (robust fallback for blur / low texture)
  rgb_*         R and B channel offsets vs G in source pixels (RGB split)
  band_dev_pct  spread of horizontal motion between 6 horizontal bands (slice glitch)
  row_tear      strongest row-to-row discontinuity vs median (tearing)
  sym_lr/sym_tb mirror symmetry (edge maps); tile = repetition score; seam_v/seam_h straight seams
  text_score    area fraction of text-like regions
  lowfreq       std of an 8x5 luma map (large soft gradients, light leaks)
  bar_*         black bar size per side (letterbox / pillarbox), fraction of frame
"""
from __future__ import annotations

import csv
import math
import subprocess
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from .timecode import frame_to_tc
from .util import log, tool

COLUMNS = [
    "frame", "time_s", "timecode",
    "cut_hist", "frame_diff", "corr_prev", "corr_skip",
    "luma_mean", "luma_std", "luma_p05", "luma_p95", "sat_mean", "lab_a", "lab_b",
    "sharpness", "sharp_norm", "sharp_med", "crisp", "grad_aniso",
    "dup", "err_prev", "rep_k", "rep_err",
    "tx_pct", "ty_pct", "scale", "rot_deg", "motion_inliers", "motion_pts", "flow_mag_pct", "warp_resid",
    "motion_src", "fm_resp",
    "pc_tx_pct", "pc_ty_pct", "pc_resp",
    "rgb_r_dx", "rgb_r_dy", "rgb_b_dx", "rgb_b_dy", "rgb_shift_px", "rgb_resp",
    "band_dev_pct", "row_tear",
    "sym_lr", "sym_tb", "tile", "seam_v", "seam_v_pos", "seam_h", "seam_h_pos",
    "text_score", "lowfreq", "bar_top", "bar_bottom", "bar_left", "bar_right",
    "proxy_fill",
    "audio_rms_db", "audio_onset", "beat", "downbeat",
]


def even(x: float) -> int:
    return max(2, int(round(x / 2.0)) * 2)


def fit_long_side(aspect: float, long_side: int) -> tuple[int, int]:
    if aspect >= 1:
        return even(long_side), even(long_side / aspect)
    return even(long_side * aspect), even(long_side)


def ffmpeg_frames_cmd(video: Path, w: int, h: int, hdr: bool) -> list[str]:
    vf = []
    if hdr:
        vf.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
                  "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
    vf.append(f"scale={w}:{h}:flags=area,setsar=1")
    return [tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(video), "-map", "0:v:0",
            "-fps_mode", "passthrough", "-vf", ",".join(vf), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]


def iter_frames(video: Path, w: int, h: int, hdr: bool = False):
    """Yield (index, frame) for every decoded frame, in display order."""
    proc = subprocess.Popen(ffmpeg_frames_cmd(video, w, h, hdr), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, bufsize=w * h * 3 * 8)
    size = w * h * 3
    i = 0
    try:
        while True:
            buf = proc.stdout.read(size)
            if not buf or len(buf) < size:
                break
            yield i, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            i += 1
    finally:
        proc.stdout.close()
        err = proc.stderr.read().decode("utf-8", "replace")
        proc.wait()
        if proc.returncode not in (0, None) and i == 0:
            raise RuntimeError(f"ffmpeg failed to decode {video}:\n{err[-1500:]}")


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum() / den) if den > 1e-6 else float("nan")


class FrameMetrics:
    def __init__(self, w: int, h: int, tw: int, th: int, src_w: int, cfg: dict):
        self.w, self.h, self.tw, self.th = w, h, tw, th
        self.src_scale = src_w / float(w)
        self.K = int(cfg["repeat_search_frames"])
        self.dup_thr = float(cfg["dup_frame_diff"])
        self.hist = deque(maxlen=self.K)     # gray thumbs: hist[0] = frame t-1, hist[1] = t-2, ...
        self.prev = None
        self.w2, self.h2 = w // 2, h // 2
        self.win2 = cv2.createHanningWindow((self.w2, self.h2), cv2.CV_32F)
        self.nb = 6
        self.bh = self.h2 // self.nb
        self.bwin = cv2.createHanningWindow((self.w2, self.bh), cv2.CV_32F)
        self.k709 = np.array([[0.0722, 0.7152, 0.2126]], np.float32)
        self.vals = np.arange(256, dtype=np.float64)
        self.close_k = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1))
        self.grad_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.lk = dict(winSize=(21, 21), maxLevel=4,
                       criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
        cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
        self.center = np.array([cx, cy, 1.0])
        # Fourier-Mellin fallback (rotation/scale): centred square, band-pass that survives motion blur
        self.fm_size = 256 if min(w, h) >= 256 else (min(w, h) // 2) * 2
        fs = self.fm_size
        self.fm_win = cv2.createHanningWindow((fs, fs), cv2.CV_32F)
        yy, xx = np.mgrid[-fs // 2:fs // 2, -fs // 2:fs // 2] / float(fs)
        rr = np.hypot(xx, yy)
        self.fm_bp = (rr / 0.06 * np.exp(-(rr / 0.12) ** 2)).astype(np.float32)
        # RGB split analysis size (long side 320) and search range (+-12 px at that size)
        self.rw, self.rh = fit_long_side(w / float(h), 320)
        self.rgb_scale = src_w / float(self.rw)
        self.rgb_search = 12

    # ------------------------------------------------------------------ helpers
    def _luma_stats(self, y: np.ndarray):
        hist = cv2.calcHist([y], [0], None, [256], [0, 256]).ravel().astype(np.float64)
        tot = hist.sum()
        mean = float((hist * self.vals).sum() / tot)
        std = float(math.sqrt(max(0.0, (hist * (self.vals - mean) ** 2).sum() / tot)))
        cdf = np.cumsum(hist) / tot
        p05 = float(np.searchsorted(cdf, 0.05))
        p95 = float(np.searchsorted(cdf, 0.95))
        return mean, std, p05, p95

    def _fm_spec(self, g: np.ndarray) -> np.ndarray:
        """Band-passed log-magnitude spectrum in log-polar form (Fourier-Mellin), for a centred square."""
        h, w = g.shape
        s = self.fm_size
        y0, x0 = max(0, (h - s) // 2), max(0, (w - s) // 2)
        c = g[y0:y0 + s, x0:x0 + s].astype(np.float32)
        if c.shape != (s, s):
            c = cv2.resize(c, (s, s))
        M = np.abs(np.fft.fftshift(np.fft.fft2(c * self.fm_win)))
        spec = (np.log1p(M) * self.fm_bp).astype(np.float32)
        return cv2.warpPolar(spec, (s, s), (s / 2, s / 2), s // 2, cv2.WARP_POLAR_LOG | cv2.INTER_LINEAR)

    def _fm_motion(self, pg: np.ndarray, g: np.ndarray, out: dict) -> dict:
        """Fallback when feature tracking fails (fast spins / zooms with blur): rotation + scale from the
        magnitude spectra (translation-invariant), then translation by phase correlation."""
        s = self.fm_size
        (dx, dy), resp = cv2.phaseCorrelate(self._fm_spec(pg), self._fm_spec(g))
        out["fm_resp"] = float(resp)
        if resp < 0.12:
            return out
        rot = ((-dy * 360.0 / s + 90.0) % 180.0) - 90.0           # same sign convention as the LK path
        scale = 1.0 / math.exp(dx * math.log(s // 2) / s)
        M = cv2.getRotationMatrix2D((self.center[0], self.center[1]), -rot, scale)
        warped = cv2.warpAffine(pg, M, (self.w, self.h), borderMode=cv2.BORDER_REFLECT)
        (tx, ty), tr = cv2.phaseCorrelate(warped.astype(np.float32), g.astype(np.float32))
        out.update(scale=float(scale), rot_deg=float(rot), motion_src=2,
                   tx_pct=float(tx / self.w * 100.0) if tr > 0.05 else np.nan,
                   ty_pct=float(ty / self.h * 100.0) if tr > 0.05 else np.nan)
        return out

    def _motion(self, pg: np.ndarray, g: np.ndarray) -> dict:
        out = dict(tx_pct=np.nan, ty_pct=np.nan, scale=np.nan, rot_deg=np.nan, motion_inliers=np.nan,
                   motion_pts=0, flow_mag_pct=np.nan, warp_resid=np.nan, motion_src=0, fm_resp=np.nan)
        p0 = cv2.goodFeaturesToTrack(pg, maxCorners=300, qualityLevel=0.01, minDistance=8, blockSize=7)
        if p0 is None or len(p0) < 15:
            return self._fm_motion(pg, g, out)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(pg, g, p0, None, **self.lk)
        if p1 is None:
            return self._fm_motion(pg, g, out)
        p0b, st2, _ = cv2.calcOpticalFlowPyrLK(g, pg, p1, None, **self.lk)
        fb = np.linalg.norm((p0 - p0b).reshape(-1, 2), axis=1)
        good = (st.ravel() == 1) & (st2.ravel() == 1) & (fb < 1.0)
        out["motion_pts"] = int(good.sum())
        if good.sum() < 20:
            return self._fm_motion(pg, g, out)
        a = p0.reshape(-1, 2)[good]
        b = p1.reshape(-1, 2)[good]
        M, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=1.5,
                                             maxIters=2000, confidence=0.995, refineIters=10)
        if M is None:
            return self._fm_motion(pg, g, out)
        out["motion_inliers"] = float(inl.sum() / len(a))   # kept even on fallback: low = parallax
        if out["motion_inliers"] < 0.45:
            return self._fm_motion(pg, g, out)
        out["motion_src"] = 1
        s = math.hypot(M[0, 0], M[1, 0])
        rot = math.degrees(math.atan2(M[1, 0], M[0, 0]))
        c2 = M @ self.center
        out.update(
            tx_pct=float((c2[0] - self.center[0]) / self.w * 100.0),
            ty_pct=float((c2[1] - self.center[1]) / self.h * 100.0),
            scale=float(s), rot_deg=float(rot),
            motion_inliers=float(inl.sum() / len(a)),
            flow_mag_pct=float(np.median(np.linalg.norm(b - a, axis=1)) / self.w * 100.0),
        )
        warped = cv2.warpAffine(pg, M, (self.w, self.h), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        valid = cv2.warpAffine(np.full_like(pg, 255), M, (self.w, self.h), flags=cv2.INTER_NEAREST,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        valid = cv2.erode(valid, None, iterations=3) > 0
        if valid.mean() > 0.3:
            out["warp_resid"] = float(np.abs(warped.astype(np.int16) - g.astype(np.int16))[valid].mean())
        return out

    def _rgb_shift(self, f: np.ndarray) -> dict:
        """Channel misalignment via 1-D cross-correlation of edge-magnitude maps (R vs G, B vs G),
        horizontally and vertically. Robust where channels are not copies of each other (saturated
        colours), unlike phase correlation. Shifts in source pixels; gain = corr(peak) - corr(0)."""
        small = cv2.resize(f, (self.rw, self.rh), interpolation=cv2.INTER_AREA).astype(np.float32)
        b, g, r = cv2.split(small)
        out = {}
        gains = []
        S = self.rgb_search
        for ax in ("x", "y"):
            dx, dy = (1, 0) if ax == "x" else (0, 1)
            G = np.abs(cv2.Sobel(g, cv2.CV_32F, dx, dy, ksize=3))
            G -= G.mean()
            axis = 1 if ax == "x" else 0
            n = G.shape[axis]
            FG = np.conj(np.fft.rfft(G, axis=axis))
            for name, ch in (("r", r), ("b", b)):
                C = np.abs(cv2.Sobel(ch, cv2.CV_32F, dx, dy, ksize=3))
                C -= C.mean()
                den = math.sqrt(float((C * C).sum()) * float((G * G).sum())) + 1e-6
                xc = np.fft.irfft((np.fft.rfft(C, axis=axis) * FG).sum(axis=1 - axis), n=n) / den
                vals = np.r_[xc[-S:], xc[:S + 1]]          # shifts -S..S
                k = int(np.argmax(vals))
                if k == 0 or k == len(vals) - 1:      # peak on the search boundary: not a real match
                    out[f"rgb_{name}_d{ax}"] = 0.0
                    gains.append(0.0)
                    continue
                sub = 0.0
                d = vals[k - 1] - 2 * vals[k] + vals[k + 1]
                if d < 0:
                    sub = 0.5 * (vals[k - 1] - vals[k + 1]) / d
                shift = (k - S + sub) * self.rgb_scale
                gain = float(vals[k] - xc[0])
                out[f"rgb_{name}_d{ax}"] = shift if gain >= 0.05 else 0.0   # weak peaks: colour-gradient contours, not a split
                gains.append(gain)
        out["rgb_shift_px"] = max(abs(out[k]) for k in ("rgb_r_dx", "rgb_r_dy", "rgb_b_dx", "rgb_b_dy"))
        out["rgb_resp"] = max(gains)
        return out

    def _text_score(self, g: np.ndarray) -> float:
        grad = cv2.morphologyEx(g, cv2.MORPH_GRADIENT, self.grad_k)
        thr, _ = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        _, bw = cv2.threshold(grad, max(thr, 40), 255, cv2.THRESH_BINARY)
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, self.close_k)
        cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = 0
        hmax = 0.15 * self.h
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if 6 <= h <= hmax and w >= 2 * h and w >= 16:
                fill = cv2.countNonZero(bw[y:y + h, x:x + w]) / float(w * h)
                if fill > 0.45:
                    area += w * h
        return area / float(self.w * self.h)

    @staticmethod
    def _bars(y: np.ndarray):
        def run_len(profile_mean, profile_max):
            n = 0
            for m, mx in zip(profile_mean, profile_max):
                if m < 6 and mx < 24:
                    n += 1
                else:
                    break
            return n
        rm, rx = y.mean(axis=1), y.max(axis=1)
        cm, cx = y.mean(axis=0), y.max(axis=0)
        H, W = y.shape
        return (run_len(rm, rx) / H, run_len(rm[::-1], rx[::-1]) / H,
                run_len(cm, cx) / W, run_len(cm[::-1], cx[::-1]) / W)

    # ------------------------------------------------------------------ main
    def compute(self, f: np.ndarray):
        r = {}
        gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        y = cv2.transform(f, self.k709)
        lm, ls, p05, p95 = self._luma_stats(y)
        r["luma_mean"], r["luma_std"] = lm / 2.55, ls / 2.55
        r["luma_p05"], r["luma_p95"] = p05 / 2.55, p95 / 2.55

        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        hs = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hs, hs, 1, 0, cv2.NORM_L1)
        hv = cv2.calcHist([hsv], [2], None, [32], [0, 256])
        cv2.normalize(hv, hv, 1, 0, cv2.NORM_L1)
        r["sat_mean"] = float(hsv[..., 1].mean()) / 2.55

        thumb = cv2.resize(f, (self.tw, self.th), interpolation=cv2.INTER_AREA)
        lab = cv2.cvtColor(thumb, cv2.COLOR_BGR2LAB)
        r["lab_a"] = float(lab[..., 1].mean()) - 128.0
        r["lab_b"] = float(lab[..., 2].mean()) - 128.0
        tg = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY).astype(np.float32)

        g2 = cv2.resize(gray, (self.w2, self.h2), interpolation=cv2.INTER_AREA)
        lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
        r["sharpness"] = float(lap.var())
        r["sharp_norm"] = r["sharpness"] / (ls * ls + 4.0)
        # median over a 4x3 grid of contrast-normalised cell sharpness: a local overlay (text, logo)
        # changes a few cells only, a real blur changes all of them
        cells = []
        ch_, cw_ = self.h // 3, self.w // 4
        yf = y.astype(np.float32)
        for gy_ in range(3):
            for gx_ in range(4):
                lc = lap[gy_ * ch_:(gy_ + 1) * ch_, gx_ * cw_:(gx_ + 1) * cw_]
                yc = yf[gy_ * ch_:(gy_ + 1) * ch_, gx_ * cw_:(gx_ + 1) * cw_]
                cells.append(float(lc.var()) / (float(yc.var()) + 4.0))
        r["sharp_med"] = float(np.median(cells))
        # edge crispness: Laplacian energy relative to gradient energy on the strongest 10% of edges.
        # Blur smears edges (drops ~1/sigma^2); a scene that simply has fewer / softer-textured areas
        # keeps crisp edges, so camera moves over changing content do not look like blur.
        gxf = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gyf = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        G2 = (gxf * gxf + gyf * gyf).ravel()
        kth = int(0.9 * G2.size)
        thr_g = float(np.partition(G2, kth)[kth])
        strong = G2 >= max(thr_g, 400.0)
        r["crisp"] = (float((lap.ravel()[strong] ** 2).mean()) / float(G2[strong].mean())
                      if strong.sum() > 50 else np.nan)
        gx = cv2.Sobel(g2, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(g2, cv2.CV_32F, 0, 1, ksize=3)
        r["grad_aniso"] = math.log((float(np.abs(gx).mean()) + 1.0) / (float(np.abs(gy).mean()) + 1.0))
        gb = cv2.GaussianBlur(gray, (3, 3), 0)

        # stateless structure metrics
        rd = np.abs(np.diff(gray.astype(np.int16), axis=0)).mean(axis=1)
        r["row_tear"] = float(rd.max() / (np.median(rd) + 2.0))
        d16 = g2.astype(np.int16)
        colfrac = (np.abs(np.diff(d16, axis=1)) > 12).mean(axis=0)
        rowfrac = (np.abs(np.diff(d16, axis=0)) > 12).mean(axis=1)
        mc, mr = max(2, int(0.04 * len(colfrac))), max(2, int(0.04 * len(rowfrac)))
        cv_ = colfrac[mc:-mc]
        rv_ = rowfrac[mr:-mr]
        r["seam_v"] = float(cv_.max()) if len(cv_) else np.nan
        r["seam_v_pos"] = float((np.argmax(cv_) + mc + 1) / g2.shape[1]) if len(cv_) else np.nan
        r["seam_h"] = float(rv_.max()) if len(rv_) else np.nan
        r["seam_h_pos"] = float((np.argmax(rv_) + mr + 1) / g2.shape[0]) if len(rv_) else np.nan
        g4 = cv2.resize(g2, (self.w2 // 2, self.h2 // 2), interpolation=cv2.INTER_AREA).astype(np.float32)
        e = cv2.magnitude(cv2.Sobel(g4, cv2.CV_32F, 1, 0), cv2.Sobel(g4, cv2.CV_32F, 0, 1))
        eh, ew = e.shape
        r["sym_lr"] = _corr(e[:, :ew // 2], e[:, ew - ew // 2:][:, ::-1])
        r["sym_tb"] = _corr(e[:eh // 2], e[eh - eh // 2:][::-1])
        tiles = []
        for k in (2, 3):
            dx, dy = ew // k, eh // k
            tiles.append(_corr(e[:, :ew - dx], e[:, dx:]))
            tiles.append(_corr(e[:eh - dy], e[dy:]))
        tiles = [t for t in tiles if np.isfinite(t)]
        r["tile"] = max(tiles) if tiles else np.nan
        r["text_score"] = self._text_score(gray)
        r["lowfreq"] = float(cv2.resize(y, (8, 5), interpolation=cv2.INTER_AREA).std()) / 2.55
        r["bar_top"], r["bar_bottom"], r["bar_left"], r["bar_right"] = self._bars(y)

        nan_keys = ["cut_hist", "frame_diff", "corr_prev", "corr_skip", "err_prev", "rep_err",
                    "pc_tx_pct", "pc_ty_pct", "pc_resp", "rgb_r_dx", "rgb_r_dy", "rgb_b_dx", "rgb_b_dy",
                    "rgb_shift_px", "rgb_resp", "band_dev_pct"]
        for k in nan_keys:
            r[k] = np.nan
        r["dup"], r["rep_k"] = 0, 0
        r.update(tx_pct=np.nan, ty_pct=np.nan, scale=np.nan, rot_deg=np.nan, motion_inliers=np.nan,
                 motion_pts=0, flow_mag_pct=np.nan, warp_resid=np.nan, motion_src=0, fm_resp=np.nan)

        # RGB channel misalignment (stateless): cross-correlate edge maps of R and B against G
        r.update(self._rgb_shift(f))

        p = self.prev
        if p is not None:
            r["frame_diff"] = float(cv2.absdiff(gb, p["gb"]).mean())
            r["cut_hist"] = 0.5 * (cv2.compareHist(p["hs"], hs, cv2.HISTCMP_BHATTACHARYYA)
                                   + cv2.compareHist(p["hv"], hv, cv2.HISTCMP_BHATTACHARYYA))
            r["corr_prev"] = _corr(tg, p["tg"])
            if len(self.hist) >= 2:
                r["corr_skip"] = _corr(tg, self.hist[1])
            r["dup"] = int(r["frame_diff"] < self.dup_thr)
            # repeats: errs[j] = thumb difference to frame t-1-j
            errs = np.abs(np.stack(self.hist) - tg).mean(axis=(1, 2))
            r["err_prev"] = float(errs[0])
            if len(errs) >= 2:
                j = int(np.argmin(errs[1:]) + 1)
                r["rep_k"], r["rep_err"] = j + 1, float(errs[j])
            r.update(self._motion(p["g"], gray))
            (dx, dy), resp = cv2.phaseCorrelate(p["g2f"], g2.astype(np.float32), self.win2)
            r["pc_tx_pct"] = dx / self.w2 * 100.0
            r["pc_ty_pct"] = dy / self.h2 * 100.0
            r["pc_resp"] = float(resp)
            # slice-glitch metric: horizontal shift of 6 bands vs previous frame, minus the straight-line
            # trend over the bands (rotation / zoom / pan move bands linearly with y; slices do not)
            ys, dxs = [], []
            g2f = g2.astype(np.float32)
            for i in range(self.nb):
                a = p["g2f"][i * self.bh:(i + 1) * self.bh]
                b = g2f[i * self.bh:(i + 1) * self.bh]
                (bdx_, _), br = cv2.phaseCorrelate(a, b, self.bwin)
                if br > 0.2:
                    ys.append(i)
                    dxs.append(bdx_)
            if len(dxs) >= 4:
                fit = np.polyval(np.polyfit(ys, dxs, 1), ys)
                r["band_dev_pct"] = float(np.abs(np.asarray(dxs) - fit).max()) / self.w2 * 100.0

        # update state
        self.prev = {"g": gray, "gb": gb, "hs": hs, "hv": hv, "tg": tg, "g2f": g2.astype(np.float32)}
        self.hist.appendleft(tg)
        return r, thumb


def run_signal_pass(video: Path, info: dict, cfg: dict, out_dir: Path, fps: float,
                    est_frames: int | None, proxy_fill: np.ndarray | None = None):
    acfg = cfg["analysis"]
    v = info["video"]
    w, h = fit_long_side(v["display_aspect"], acfg["long_side_px"])
    tw, th = fit_long_side(v["display_aspect"], acfg["thumb_long_side_px"])
    fm = FrameMetrics(w, h, tw, th, v["display_width"], acfg)
    cache = out_dir / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    thumbs_path = cache / "thumbs.u8"
    rows = {k: [] for k in COLUMNS if k not in ("frame", "time_s", "timecode")}
    import time as _t
    t0 = _t.time()
    n = 0
    with open(thumbs_path, "wb") as tf:
        for i, frame in iter_frames(video, w, h, v.get("hdr", False)):
            m, thumb = fm.compute(frame)
            for k in rows:
                if k in m:
                    rows[k].append(m[k])
            tf.write(thumb.tobytes())
            n = i + 1
            if n % 500 == 0:
                rate = n / max(1e-6, _t.time() - t0)
                eta = f", ETA {((est_frames or n) - n) / rate:.0f}s" if est_frames else ""
                log(f"signal pass: frame {n}{'/' + str(est_frames) if est_frames else ''} ({rate:.0f} fps{eta})")
    if n == 0:
        raise RuntimeError("no frames decoded")
    log(f"signal pass done: {n} frames in {_t.time() - t0:.1f}s at {w}x{h}")
    metrics = {k: np.asarray(vv, dtype=np.float64) for k, vv in rows.items() if len(vv) == n}
    metrics["frame"] = np.arange(n, dtype=np.float64)
    metrics["time_s"] = metrics["frame"] / fps
    pf = np.zeros(n) if proxy_fill is None else np.resize(proxy_fill.astype(np.float64), n)
    metrics["proxy_fill"] = pf
    meta = {"n_frames": n, "analysis_w": w, "analysis_h": h, "thumb_w": tw, "thumb_h": th}
    return metrics, meta


def load_thumbs(out_dir: Path, meta: dict) -> np.ndarray:
    p = out_dir / "cache" / "thumbs.u8"
    return np.memmap(p, dtype=np.uint8, mode="r",
                     shape=(meta["n_frames"], meta["thumb_h"], meta["thumb_w"], 3))


def save_metrics(metrics: dict, out_dir: Path, fps: float, drop_tc: bool) -> Path:
    n = len(metrics["frame"])
    np.savez_compressed(out_dir / "cache" / "metrics.npz", **{k: v for k, v in metrics.items()})
    path = out_dir / "metrics.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(COLUMNS)
        for i in range(n):
            row = []
            for c in COLUMNS:
                if c == "timecode":
                    row.append(frame_to_tc(i, fps, drop_tc))
                    continue
                arr = metrics.get(c)
                if arr is None:
                    row.append("")
                    continue
                val = arr[i]
                if c in ("frame", "dup", "rep_k", "motion_pts", "motion_src", "beat", "downbeat", "proxy_fill"):
                    row.append("" if not np.isfinite(val) else str(int(val)))
                elif not np.isfinite(val):
                    row.append("")
                else:
                    row.append(f"{val:.6g}")
            wr.writerow(row)
    return path


def load_metrics(out_dir: Path) -> dict:
    d = np.load(out_dir / "cache" / "metrics.npz")
    return {k: d[k] for k in d.files}
