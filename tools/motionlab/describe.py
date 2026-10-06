"""Auto-descriptions: beat/drop timing, origin guess (camera vs post), easing, Resolve rebuild recipe.

These are DRAFTS written from measurements. During /analyze-reference Claude looks at every contact
sheet and replaces them with a reviewed classification (review.json), keeping the measured numbers.
"""
from __future__ import annotations

import numpy as np

from . import taxonomy
from .timecode import frame_to_tc

POST_ONLY = {
    "crossfade": "two different shots are visible at once in every blended frame - only an edit can do that",
    "dip_black": "the picture fades to black and a different shot fades in - an edit transition",
    "dip_white": "the picture fades to white between shots - an edit transition",
    "fade_in": "the video fades up from black - an edit fade",
    "fade_out": "the video fades down to black - an edit fade",
    "wipe": "a straight edge separates two different shots - only possible as an edit transition",
    "mask_reveal": "two different shots are separated by a shaped mask - a compositing effect",
    "luma_fade": "the new shot appears through the brightness of the old one - a keyed transition",
    "push_slide": "two shots move together as flat layers - an edit transition",
    "zoom_transition": "the zoom ramps into a hard cut and continues on the next shot - a designed transition",
    "freeze": "identical frames repeat while motion stops - a frame hold added in the edit",
    "stutter": "earlier frames repeat exactly - a time effect added in the edit",
    "frame_repeat": "every other frame is an exact duplicate - a retime / stepped-frame effect",
    "strobe": "brightness alternates every frame - a strobe effect (or a strobe light; see frames)",
    "rgb_split": "colour channels are shifted against each other by whole pixels - a post effect "
                 "(lens chromatic aberration is sub-pixel and grows toward the edges)",
    "glitch": "bands of the picture are displaced - a digital glitch effect",
    "invert": "the picture turns into its negative - a colour effect",
    "sat_pop": "saturation jumps while the picture stays the same - a grade change keyed in the edit",
    "split_screen": "a straight full-length edge separates independent pictures - a composite",
    "multi_screen": "the picture repeats in tiles - a composite",
    "mirror": "the picture is an exact mirror image - a post effect (real reflections are never pixel-exact)",
    "text": "text / graphics are overlaid on the picture",
    "hard_cut": "a cut",
    "jump_cut": "a cut within the same framing",
    "flash_black": "black frames inserted between shots",
}


def beat_info(frame: float, audio: dict | None, fps: float, tol: float) -> dict | None:
    if not audio or not audio.get("available") or not audio.get("beats"):
        return None
    bf = np.array([b["frame"] for b in audio["beats"]])
    k = int(np.argmin(np.abs(bf - frame)))
    off = float(frame - bf[k])
    downs = [i for i, b in enumerate(audio["beats"]) if b["downbeat"]]
    bar = beat_in_bar = None
    if downs:
        prev = [d for d in downs if d <= k]
        if prev:
            d0 = prev[-1]
            bar = downs.index(d0) + 1
            beat_in_bar = k - d0 + 1
    drops = [d["frame"] for d in audio.get("drops", [])]
    on_drop = any(abs(frame - d) <= tol for d in drops)
    return {"beat_index": k, "beat_frame": round(float(bf[k]), 2), "offset_frames": round(off, 2),
            "on_beat": abs(off) <= tol, "downbeat": bool(audio["beats"][k]["downbeat"]),
            "bar": bar, "beat_in_bar": beat_in_bar, "on_drop": on_drop,
            "beat_period_frames": audio.get("beat_period_frames")}


def timing_summary(ev: dict, audio: dict | None, fps: float, tol: float) -> dict:
    pts = {"start": ev["start"], "key": ev["key"], "end": ev["end"]}
    out = {k: beat_info(v, audio, fps, tol) for k, v in pts.items()}
    if out["start"] is None:
        return {"text": "no audio / no beats", "on_beat": None, "on_drop": None, "points": out}
    hits = [k for k in ("key", "start", "end") if out[k]["on_beat"]]
    on_drop = any(out[k]["on_drop"] for k in out)
    if hits:
        k = hits[0]
        b = out[k]
        where = {"key": "lands", "start": "starts", "end": "ends"}[k]
        pos = f"bar {b['bar']} beat {b['beat_in_bar']}" if b["bar"] else f"beat {b['beat_index'] + 1}"
        txt = (f"{where} on the beat ({pos}{', bar start' if b['downbeat'] else ''}; "
               f"offset {b['offset_frames']:+.1f} f at {ev[k] if k != 'key' else ev['key']})")
    else:
        b = out["key"]
        txt = f"not on a beat (nearest beat {b['offset_frames']:+.1f} frames from the key frame)"
    if on_drop:
        txt += "; ON THE DROP"
    return {"text": txt, "on_beat": bool(hits), "on_drop": on_drop, "points": out}


def origin_guess(ev: dict, m: dict) -> tuple[str, str]:
    t = ev["type"]
    a, b = ev["start"], ev["end"] + 1
    if t in POST_ONLY:
        return "post", POST_ONLY[t]
    inl = np.asarray(m["motion_inliers"][a:b], float)
    inl = inl[np.isfinite(inl)]
    med_inl = float(np.median(inl)) if len(inl) else float("nan")
    if t in ("zoom_in", "zoom_out", "whip_pan", "spin", "shake"):
        if np.isfinite(med_inl) and med_inl >= 0.9:
            return "post", (f"the whole frame moves as one flat image ({med_inl:.0%} of tracked points fit a single "
                            f"2D scale/rotate/move): no parallax, so a digital move added in the edit")
        if np.isfinite(med_inl):
            return "camera", (f"only {med_inl:.0%} of tracked points fit one 2D move: parallax/perspective change "
                              f"points to a real camera move (check the sheet)")
        return "unclear", "motion could not be tracked reliably (blur / low detail)"
    if t in ("flash_white", "flash"):
        comp = ev["components"][0]
        if comp.get("evidence", {}).get("on_cut"):
            return "post", "the flash covers a cut between two different shots - an edit flash"
        if t == "flash_white":
            return "post", "the whole frame turns white evenly (even the darkest areas) - an added flash"
        return "unclear", "partial brightening inside one shot: could be a real light (strobe, camera flash) or an added flash"
    if t == "blur":
        if "motion" in ev.get("sub", ""):
            return "post", "blur comes with a fast move: motion blur of a (likely added) camera move"
        return "unclear", "blur without motion: post blur or a real focus pull (focus pulls keep some plane sharp)"
    if t == "light_leak":
        return "post", "warm soft overlay that does not follow the scene geometry - an overlay (or a real lens flare)"
    if t == "speed_ramp":
        return "unclear", "motion speed changes within one shot: a speed ramp (time remap) or the subject/camera speeding up"
    if t == "flash_color":
        return "post", "the whole frame shifts to one tint for a few frames - an added colour flash"
    return "unclear", "not enough evidence to tell"


def confidence_guess(ev: dict) -> str:
    s = ev.get("score", 0.5)
    if ev["type"] in ("unknown", "speed_ramp", "text", "light_leak"):
        return "low"
    return "high" if s >= 0.85 else ("medium" if s >= 0.55 else "low")


def _pct(x):
    return f"{x:.0f}%"


def rebuild(ev: dict, fps: float) -> str:
    t = ev["type"]
    comps = {c["type"]: c for c in ev["components"]}
    c = comps.get(t, ev["components"][0])
    e = c.get("evidence", {}) or {}
    n = ev["duration_frames"]
    s0, s1 = ev["start"], ev["end"]
    if t in ("flash_white", "flash"):
        decay = e.get("decay_luma_pct", [])
        peak = "100%" if t == "flash_white" else _pct(max(10, (e.get("peak_luma_pct", 60) - e.get("luma_before_pct", 40))))
        return (f"Edit page: Solid Color generator (white) on V2 starting at frame {s0}, {n} frames long; "
                f"Inspector > Composite > Opacity keyframes {peak} on the first frame falling to 0% on frame {s1 + 1} "
                f"(measured decay {' > '.join(str(v) + '%' for v in decay)} luma), ease the last keyframe for a soft tail. "
                f"Fusion: Background (white) > Merge over MediaIn, Merge Blend keyframed 1.0 > 0.0 over {n} frames."
                + (f" Place the clip cut under the white frame ({ev['cuts'][0]})." if ev.get("cuts") else ""))
    if t == "flash_black":
        return f"Edit page: leave {n} frame(s) of gap (or a black Solid Color) between the two clips at frame {s0}."
    if t in ("dip_black", "dip_white", "fade_in", "fade_out"):
        col = "black" if "black" in t or t.startswith("fade") else "white"
        o, h, i = e.get("ramp_out_frames", 0), e.get("hold_frames", 0), e.get("ramp_in_frames", 0)
        if t == "fade_in":
            return f"Edit page: drag the clip's fade-in handle to {n} frames (or Opacity keyframes 0% > 100%)."
        if t == "fade_out":
            return f"Edit page: drag the clip's fade-out handle to {n} frames (or Opacity keyframes 100% > 0%)."
        return (f"Edit page: Video Transitions > Dissolve > 'Dip To Color Dissolve', color {col}, {n} frames, centred on "
                f"the cut. The measured shape is asymmetric (out {o} f, hold {h} f, in {i} f): to match it exactly put a "
                f"{col} Solid Color clip of {h} frames between the clips and add a {o}-frame Cross Dissolve into it and an "
                f"{i}-frame Cross Dissolve out of it.")
    if t == "crossfade":
        return (f"Edit page: Video Transitions > Dissolve > 'Cross Dissolve', duration {n} frames ({n / fps:.2f}s), "
                f"alignment Centre on Edit (frames {s0}-{s1}); easing measured: {e.get('easing', '?')}. Fusion: Merge "
                f"(Background = outgoing, Foreground = incoming) with Blend keyframed 0 > 1 over {n} frames.")
    if t == "wipe":
        return (f"Edit page: Video Transitions > Wipe > 'Edge Wipe', {n} frames, set the angle so the "
                f"{ev.get('sub', 'new shot enters from the side')}, Border 0, Feather 0 (hard edge as measured). Fusion: "
                f"Rectangle mask on the Merge foreground, keyframe its Center across the frame over {n} frames.")
    if t == "mask_reveal":
        if "iris" in ev.get("sub", ""):
            return (f"Edit page: Video Transitions > Iris > 'Iris' (circle) {n} frames. Fusion: Ellipse mask on the Merge "
                    f"foreground, Width/Height keyframed 0 > 1.5 over {n} frames, Soft Edge to taste.")
        return (f"Fusion: Polygon/B-Spline mask (or a matte from another clip) on the Merge foreground, animate the "
                f"shape over {n} frames so the incoming shot is revealed as in the sheet.")
    if t == "luma_fade":
        return (f"Fusion: Luma Keyer on the outgoing clip feeding the Merge as an alpha, animate Low/High so the "
                f"{ev.get('sub', 'bright areas')} switch first over {n} frames. Edit page approximation: "
                f"'Non-Additive Dissolve'.")
    if t == "push_slide":
        return f"Edit page: Video Transitions > Motion > 'Push' (or 'Slide'), {n} frames, direction as in the sheet."
    if t == "zoom_transition":
        out_, in_ = e.get("outgoing") or {}, e.get("incoming") or {}
        cut = e.get("cut", ev["key"])
        txt = f"Cut on frame {cut}. "
        if out_:
            k = len(out_.get("scale_per_frame", []))
            txt += (f"Outgoing clip, last {k} frames: Fusion Transform Size keyframes 1.0 > {out_.get('total_scale', 2):.2f} "
                    f"({out_.get('easing', '')}; in the Spline editor make the curve steepen toward the cut). ")
        if in_:
            k = len(in_.get("scale_per_frame", []))
            start = 1.0 / max(1e-6, in_.get("total_scale", 0.5))
            txt += (f"Incoming clip, first {k} frames: Transform Size {start:.2f} > 1.0 ({in_.get('easing', '')}). ")
        txt += ("Turn on Motion Blur in both Transform nodes (Quality 8, Shutter Angle 180-360) or add a "
                "Directional Blur (Type: Zoom) whose Length peaks at the cut.")
        return txt
    if t in ("zoom_in", "zoom_out"):
        tot = e.get("total_scale", 1.1)
        k = len(e.get("scale_per_frame", [])) or n
        return (f"Edit page Inspector > Transform > Zoom keyframes 1.00 at frame {s0 - 1} > {tot:.2f} at frame {s1} "
                f"({k} frame(s), {e.get('easing', '')}). For a punch on the beat put the keyframes 1-2 frames apart; "
                f"add Motion Blur via a Fusion Transform (Motion Blur on) for the smear.")
    if t == "whip_pan":
        return (f"Fusion: Transform Center keyframed so the frame travels ~{e.get('peak_speed_pct_per_frame', 20)}% of its "
                f"width per frame at the peak (frames {s0}-{s1}), Edges: Mirror, Motion Blur on (Quality 8+, Shutter "
                f"Angle 360) or Directional Blur (Linear) with Length keyframed to the speed."
                + (f" Cut at the blur peak (frame {ev['cuts'][0]}) and continue the move on the incoming clip."
                   if ev.get("cuts") else ""))
    if t == "spin":
        return (f"Fusion: Transform Angle keyframed {e.get('total_deg', 90):+.0f} deg over frames {s0}-{s1} "
                f"({e.get('easing', '')}), Size ~1.4 to hide the corners, Motion Blur on.")
    if t == "shake":
        return (f"Edit page: Effects > Fusion Effects > 'Camera Shake' on frames {s0}-{s1} (or Fusion: Shake modifier on "
                f"Transform Center): deviation ~{e.get('rms_jitter_pct', 1)}% of the frame, high rate, low smoothness; "
                f"keyframe the strength so it hits on the beat and decays.")
    if t == "speed_ramp":
        return (f"Edit page: Ctrl+R (Retime Controls), add speed points around frame {ev['key']}, set the speeds to "
                f"match the measured {e.get('motion_before_pct')} > {e.get('motion_after_pct')} %/frame motion, and smooth "
                f"the Retime Curve; Retime Process: Optical Flow.")
    if t == "freeze":
        return (f"Edit page: blade at frame {s0}, Ctrl+R (Retime Controls) > Freeze Frame, and set the freeze to "
                f"{n} frames ({n / fps:.2f}s); playback resumes from the next frame.")
    if t == "stutter":
        ks = e.get("repeat_distance_frames") or [4]
        k = max(set(ks), key=ks.count)
        reps = max(1, round(n / max(1, k)))
        return (f"Edit page: blade the {k}-frame chunk starting at frame {s0}, then Alt-drag copies so it plays {reps}x "
                f"back-to-back (frames {s0}-{s1}). Fusion alternative: TimeStretcher with Source Time keyframed as a "
                f"{k}-frame saw-tooth.")
    if t == "frame_repeat":
        return ("Fusion: TimeStretcher with Source Time = floor(time/2)*2 (holds every frame twice, 'on 2s'); or "
                "retime the clip to 50% with Retime Process 'Nearest' and back to the original length.")
    if t == "strobe":
        return ("Alternate 1-frame slices of the clip with 1-frame black/white Solid Color clips, or in Fusion Merge a "
                "Background with Blend expression 'time % 2'.")
    if t == "rgb_split":
        r, b = e.get("red_offset_px", [0, 0]), e.get("blue_offset_px", [0, 0])
        return (f"Fusion: three Channel Booleans nodes isolate red, green and blue (other channels set to Black); "
                f"Transform the red copy by {r[0]:+.0f} px X / {r[1]:+.0f} px Y and the blue copy by {b[0]:+.0f} px X / "
                f"{b[1]:+.0f} px Y; Merge the three back with Apply Mode 'Screen'. Keyframe the offset over frames "
                f"{s0}-{s1} (measured per frame: {', '.join(str(x) for x in e.get('shift_per_frame_px', []))} px).")
    if t == "glitch":
        return (f"Fusion: copy the clip, cut 2-4 horizontal bands with Rectangle masks, offset each with a Transform "
                f"(Center X by a few %) for frames {s0}-{s1}, Merge back, add an RGB offset on the same frames. "
                f"Quick version: Effects > Fusion Effects > 'Digital Glitch'.")
    if t == "blur":
        return (f"Edit page: Effects > ResolveFX Blur > 'Gaussian Blur', keyframe strength 0 > peak > 0 over frames "
                f"{s0}-{s1} (detail measured down to {e.get('sharpness_ratio_min', 0.2):.0%} of normal). Across a cut use "
                f"the 'Blur Dissolve' transition. Fusion: Blur node, Blur Size keyframed.")
    if t == "flash_color":
        return (f"Edit page: Solid Color generator (tint hue ~{e.get('tint_hue_deg', 0):.0f} deg in Lab a/b) on V2 for "
                f"frames {s0}-{s1}, Composite Mode 'Screen' or 'Add', Opacity keyframed peak > 0.")
    if t == "invert":
        return (f"Edit page: blade frames {s0}-{s1} and add Effects > ResolveFX Color > 'Invert Color' (or Color page: "
                f"invert the YRGB curve).")
    if t == "sat_pop":
        return (f"Color page: dynamic keyframes on a node's Saturation: {e.get('sat_before_pct')} > {e.get('sat_after_pct')} "
                f"(% of max) at frame {ev['key']}.")
    if t == "light_leak":
        return (f"Edit page: light-leak stock clip on V2 over frames {s0}-{s1}, Composite Mode 'Screen', Opacity "
                f"keyframed in/out. Fusion: FastNoise (low Detail, high Contrast, Seethe animated) > Color Corrector "
                f"(orange) > Merge Apply Mode Screen.")
    if t == "split_screen":
        return "Edit page: Effects > ResolveFX Transform > 'Video Collage', or stack clips and set Crop + Position in the Inspector."
    if t == "mirror":
        return "Effects > ResolveFX Stylize > 'Mirrors' (pick the mirror plane), or Fusion: Transform Flip + Crop > Merge."
    if t == "multi_screen":
        return "Fusion: Transform Size 0.5 with Edges: Wrap tiles the picture; or Effects > ResolveFX Transform > 'Video Collage'."
    if t == "text":
        return "Edit page: Titles > Text+ (Fusion title); match font/position from the sheet, animate with Inspector keyframes."
    return "Not classified automatically - see the description and the contact sheet."


def draft(ev: dict, m: dict, audio: dict | None, fps: float, cfg: dict, drop_tc: bool) -> dict:
    tol = cfg["audio"]["on_beat_tolerance_frames"]
    timing = timing_summary(ev, audio, fps, tol)
    origin, why = origin_guess(ev, m)
    notes = []
    for comp in ev["components"]:
        for n_ in comp.get("notes", []):
            if n_ not in notes:
                notes.append(n_)
    easing = None
    for comp in ev["components"]:
        e = comp.get("evidence") or {}
        easing = easing or e.get("easing") or e.get("easing_in")
    others = [taxonomy.label(x) for x in ev["types"][1:]]
    head = f"{ev['type_label']}" + (f" ({ev['sub']})" if ev.get("sub") else "")
    if others:
        head += " combined with " + ", ".join(others)
    return {
        "type": ev["type"], "type_label": ev["type_label"],
        "what": head + ". " + (notes[0] if notes else ""),
        "evidence": notes,
        "origin": origin, "origin_why": why,
        "duration_frames": ev["duration_frames"],
        "duration_text": f"{ev['duration_frames']} frames ({ev['duration_frames'] / fps:.2f}s), "
                         f"f{ev['start']}-{ev['end']} ({frame_to_tc(ev['start'], fps, drop_tc)} - "
                         f"{frame_to_tc(ev['end'], fps, drop_tc)})",
        "timing": timing["text"], "on_beat": timing["on_beat"], "on_drop": timing["on_drop"],
        "timing_points": timing["points"],
        "easing": easing or "n/a",
        "confidence": confidence_guess(ev),
        "rebuild": rebuild(ev, fps),
    }
