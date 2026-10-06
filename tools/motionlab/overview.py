"""overview.png: per-frame metrics over time (small multiples, one measure per panel) with beats,
drops, builds, cuts and detected events. Rendered for light (overview.png) and dark (overview_dark.png)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import taxonomy  # noqa: E402

THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
              "axis": "#c3c2b7", "beat": "#e9e8e2", "bar": "#cfcdc4",
              "s": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"], "drop": "#e34948"},
    "dark": {"surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a",
             "axis": "#383835", "beat": "#262624", "bar": "#45453f",
             "s": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"], "drop": "#e66767"},
}

# event lane: 5 classes (validated palette slots 1-5, labelled so colour is never the only cue)
CLASS_OF = {}
for _t in ("flash_white", "flash", "flash_black", "dip_black", "dip_white", "fade_in", "fade_out", "crossfade",
           "wipe", "mask_reveal", "luma_fade", "push_slide", "zoom_transition", "jump_cut"):
    CLASS_OF[_t] = 0
for _t in ("zoom_in", "zoom_out", "whip_pan", "spin", "shake", "speed_ramp"):
    CLASS_OF[_t] = 1
for _t in ("freeze", "stutter", "frame_repeat", "strobe"):
    CLASS_OF[_t] = 2
for _t in ("rgb_split", "glitch", "blur", "flash_color", "invert", "sat_pop", "light_leak"):
    CLASS_OF[_t] = 3
CLASS_NAMES = ["transition", "camera / motion", "time (freeze, stutter)", "look (colour, blur, glitch)",
               "layout / text / other"]


def _g(m, k):
    v = m.get(k)
    return np.asarray(v, dtype=float) if v is not None else None


def render(m: dict, audio: dict | None, events: list[dict], plain_cuts: list[dict], fps: float, out: Path,
           theme: str = "light") -> Path:
    T = THEMES[theme]
    n = len(m["frame"])
    t = np.arange(n) / fps
    dur = n / fps
    width_in = float(np.clip(dur * 30 / 100, 18, 90))
    panels = ["audio", "cut", "luma", "sharp", "diff", "move", "zoom", "rot", "rgb", "events"]
    heights = [1.1, 1.0, 1.1, 0.9, 0.9, 1.0, 0.9, 0.8, 0.8, 1.0]
    fig, axes = plt.subplots(len(panels), 1, figsize=(width_in, sum(heights) * 1.25), sharex=True,
                             gridspec_kw={"height_ratios": heights, "hspace": 0.32}, facecolor=T["surface"])
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9})

    beats = [b["t"] for b in (audio or {}).get("beats", [])] if audio and audio.get("available") else []
    downs = [b["t"] for b in (audio or {}).get("beats", []) if b.get("downbeat")] if beats else []
    drops = [d["t"] for d in (audio or {}).get("drops", [])] if beats else []
    builds = (audio or {}).get("builds", []) if beats else []
    cut_t = [c["frame"] / fps for c in plain_cuts]

    for ax in axes:
        ax.set_facecolor(T["surface"])
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(T["axis"])
        ax.tick_params(colors=T["muted"], labelsize=8, length=0)
        ax.grid(axis="y", color=T["grid"], linewidth=0.6)
        ax.set_axisbelow(True)
        for b in beats:
            ax.axvline(b, color=T["beat"], linewidth=0.6, zorder=0)
        for b in downs:
            ax.axvline(b, color=T["bar"], linewidth=0.8, zorder=0)
        for bl in builds:
            ax.axvspan(bl["start_t"], bl["end_t"], color=T["s"][3], alpha=0.10, linewidth=0, zorder=0)
        for d in drops:
            ax.axvline(d, color=T["drop"], linewidth=1.2, zorder=1)

    def title(ax, txt):
        ax.set_title(txt, loc="left", fontsize=9.5, color=T["ink2"], pad=3)

    ax = axes[0]
    if audio and audio.get("available") and "audio_rms_db" in m:
        ax.plot(t, _g(m, "audio_rms_db"), color=T["s"][0], linewidth=1.0)
        lo = np.nanpercentile(_g(m, "audio_rms_db"), 2)
        ax.set_ylim(bottom=lo)
        for d in drops:
            ax.text(d, 1.0, " DROP", transform=ax.get_xaxis_transform(), color=T["drop"], fontsize=8.5,
                    va="top", fontweight="bold")
        for bl in builds:
            ax.text(bl["start_t"], 1.0, " build", transform=ax.get_xaxis_transform(), color=T["ink2"],
                    fontsize=8, va="top")
        title(ax, f"Audio energy (dB)  ·  {audio.get('bpm', 0):.1f} BPM  ·  thin lines = beats, darker = bar starts")
    else:
        title(ax, "Audio: none")

    ax = axes[1]
    ax.plot(t, np.nan_to_num(_g(m, "cut_hist")), color=T["s"][0], linewidth=0.9)
    ax.set_ylim(0, 1.0)
    for c in cut_t:
        ax.axvline(c, ymin=0.82, ymax=1.0, color=T["ink"], linewidth=1.0)
    title(ax, "Cut score: colour-histogram change vs previous frame (0-1)  ·  ticks = hard cuts")

    ax = axes[2]
    ax.fill_between(t, _g(m, "luma_p05"), _g(m, "luma_p95"), color=T["s"][0], alpha=0.15, linewidth=0)
    ax.plot(t, _g(m, "luma_mean"), color=T["s"][0], linewidth=1.0, label="luma mean (band = 5th-95th pct)")
    ax.plot(t, _g(m, "sat_mean"), color=T["s"][1], linewidth=1.0, label="saturation mean")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), borderaxespad=0.1, fontsize=8, frameon=False, labelcolor=T["ink2"], ncol=2)
    title(ax, "Luma and saturation (%)")

    ax = axes[3]
    sn = _g(m, "sharp_norm")
    ax.plot(t, np.where(np.isfinite(sn) & (sn > 0), sn, np.nan), color=T["s"][0], linewidth=0.9)
    ax.set_yscale("log")
    title(ax, "Sharpness (Laplacian variance / contrast, log scale)  ·  dips = blur")

    ax = axes[4]
    ax.plot(t, np.nan_to_num(_g(m, "frame_diff")), color=T["s"][0], linewidth=0.9)
    dup = np.nan_to_num(_g(m, "dup")) > 0.5
    if dup.any():
        ax.scatter(t[dup], np.zeros(int(dup.sum())), s=9, color=T["s"][1], zorder=3, label="duplicate frame")
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), borderaxespad=0.1, fontsize=8, frameon=False, labelcolor=T["ink2"])
    title(ax, "Frame change (mean abs. difference to previous frame, 0-255)")

    ax = axes[5]
    ax.plot(t, _g(m, "tx_pct"), color=T["s"][0], linewidth=0.9, label="horizontal")
    ax.plot(t, _g(m, "ty_pct"), color=T["s"][1], linewidth=0.9, label="vertical")
    ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), borderaxespad=0.1, fontsize=8, frameon=False, labelcolor=T["ink2"], ncol=2)
    title(ax, "Global motion (% of frame per frame)")

    ax = axes[6]
    sc = _g(m, "scale")
    ax.plot(t, (sc - 1) * 100, color=T["s"][0], linewidth=0.9)
    title(ax, "Zoom (% scale change per frame, + = zooming in)")

    ax = axes[7]
    ax.plot(t, _g(m, "rot_deg"), color=T["s"][0], linewidth=0.9)
    title(ax, "Rotation (degrees per frame)")

    ax = axes[8]
    ax.plot(t, np.nan_to_num(_g(m, "rgb_shift_px")), color=T["s"][0], linewidth=0.9)
    title(ax, "RGB channel misalignment (source pixels)")

    ax = axes[9]
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.grid(False)
    used = set()
    for i, ev in enumerate(events):
        cls = CLASS_OF.get(ev["type"], 4)
        used.add(cls)
        a, b = ev["start"] / fps, (ev["end"] + 1) / fps
        y0 = 0.08 + 0.42 * (i % 2)
        ax.add_patch(plt.Rectangle((a, y0), max(b - a, 1.5 / fps), 0.38, color=T["s"][cls], linewidth=0))
        ax.text(a, y0 + 0.40, f"{ev['id']} {taxonomy.label(ev['type'])}", fontsize=7.5, color=T["ink"],
                va="bottom", clip_on=True)
    for c in cut_t:
        ax.axvline(c, ymin=0, ymax=0.06, color=T["ink"], linewidth=1.0)
    handles = [plt.Rectangle((0, 0), 1, 1, color=T["s"][k]) for k in sorted(used)]
    if handles:
        ax.legend(handles, [CLASS_NAMES[k] for k in sorted(used)], loc="upper right", fontsize=8, frameon=False,
                  labelcolor=T["ink2"], ncol=len(handles), bbox_to_anchor=(1.0, 1.32))
    title(ax, "Detected events (IDs match the report)  ·  ticks = plain hard cuts")
    ax.set_xlim(0, dur)
    ax.set_xlabel("time (s)", color=T["muted"], fontsize=8.5)

    # frame numbers along the top of the first panel
    top = axes[0].secondary_xaxis("top", functions=(lambda s: s * fps, lambda f: f / fps))
    top.tick_params(colors=T["muted"], labelsize=8, length=0)
    top.set_xlabel("frame", color=T["muted"], fontsize=8.5)
    for sp in top.spines.values():
        sp.set_visible(False)

    fig.subplots_adjust(left=0.035, right=0.995, top=0.95, bottom=0.04)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100, facecolor=T["surface"])
    plt.close(fig)
    return out
