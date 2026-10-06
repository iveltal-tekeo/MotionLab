"""Audio analysis: tempo, beats, onsets, best-effort downbeats, RMS energy, builds and drops.

All times returned are VIDEO times (seconds from video frame 0), so frame = t * fps.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .util import log, run, tool


def extract_wav(src: Path, dst: Path, sr: int) -> bool:
    r = run([tool("ffmpeg"), "-y", "-v", "error", "-i", str(src), "-map", "0:a:0", "-vn", "-ac", "1",
             "-ar", str(sr), "-c:a", "pcm_s16le", str(dst)], check=False)
    return r.returncode == 0 and dst.exists() and dst.stat().st_size > 1000


def _smooth(x: np.ndarray, n: int) -> np.ndarray:
    n = max(1, int(n))
    if n == 1 or len(x) < n:
        return x.copy()
    k = np.ones(n) / n
    pad = n // 2
    xp = np.pad(x, (pad, n - 1 - pad), mode="edge")
    return np.convolve(xp, k, mode="valid")


def _z(x: np.ndarray) -> np.ndarray:
    s = np.std(x)
    return (x - np.mean(x)) / s if s > 1e-9 else np.zeros_like(x)


def analyze(wav: Path, fps: float, n_frames: int, offset_s: float, cfg: dict) -> dict:
    import librosa
    import soundfile as sf

    y, sr = sf.read(str(wav), dtype="float32", always_2d=False)
    if y.ndim > 1:
        y = y.mean(axis=1)
    hop = int(cfg["hop_length"])
    dur = len(y) / sr
    if dur < 1.0 or float(np.max(np.abs(y))) < 1e-4:
        return {"available": False, "reason": "audio too short or silent"}

    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    env_t = librosa.times_like(oenv, sr=sr, hop_length=hop)
    # trim=False: librosa's trimming drops whole quieter sections at the end of a song
    tempo, bfr = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, units="frames",
                                         tightness=float(cfg["beat_tightness"]), trim=False)
    bfr = np.asarray(bfr, dtype=int)
    tempo_lib = float(np.atleast_1d(tempo)[0]) if np.size(tempo) else 0.0
    shift = cfg["beat_offset_ms"] / 1000.0

    # energy
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
    rms_t = librosa.times_like(rms, sr=sr, hop_length=hop)
    rms_db = 20 * np.log10(np.maximum(rms, 1e-5))

    # drop beats that fall in silence
    if len(bfr):
        floor = float(rms_db.max()) - float(cfg["silence_db_below_peak"])
        keep = rms_db[np.clip(bfr, 0, len(rms_db) - 1)] > floor
        bfr = bfr[keep]

    # beat_track lands ~1-2 hops after the attack: snap each beat (and onset) to the peak of a
    # fine-resolution onset envelope so on-beat checks are accurate to a few milliseconds
    fh = int(cfg["refine_hop"])
    fenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=fh, n_fft=int(cfg["refine_n_fft"]), n_mels=64)
    ft = librosa.times_like(fenv, sr=sr, hop_length=fh)

    def refine(times, before, after):
        out = []
        for tb in times:
            i0, i1 = np.searchsorted(ft, tb - before), np.searchsorted(ft, tb + after)
            out.append(float(ft[i0 + int(np.argmax(fenv[i0:i1]))]) if i1 > i0 else float(tb))
        return np.asarray(out)

    beat_t_coarse = librosa.frames_to_time(bfr, sr=sr, hop_length=hop)
    # the tracker can extrapolate a phantom beat into the last few milliseconds of the file
    keep = beat_t_coarse < dur - 0.08
    bfr, beat_t_coarse = bfr[keep], beat_t_coarse[keep]
    beat_t_audio = refine(beat_t_coarse, 0.06, 0.03) + shift
    # no audio exists before t=0, so a beat in the first 60 ms cannot be refined: use the coarse time
    # minus the tracker's typical ~20 ms lag
    early = beat_t_coarse < 0.06
    beat_t_audio[early] = np.maximum(0.0, beat_t_coarse[early] - 0.02) + shift
    if len(beat_t_audio) >= 8:
        bpm = 60.0 / float(np.median(np.diff(beat_t_audio)))
    else:
        bpm = tempo_lib
    onset_t_audio = refine(librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop,
                                                      units="time"), 0.04, 0.02) + shift
    fr_per_s = sr / hop
    # average in the power domain (dB averaging over-weights quiet gaps between hits)
    pw = np.maximum(rms, 1e-5) ** 2
    e_fast = 10 * np.log10(_smooth(pw, round(0.25 * fr_per_s)))
    e_slow = 10 * np.log10(_smooth(pw, round(1.0 * fr_per_s)))

    # low band (kick/bass) energy + onset, chroma for harmonic change
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
    low = S[freqs < 150].sum(axis=0)
    low_raw_db = 20 * np.log10(np.maximum(low, 1e-5))
    low_on = np.maximum(0, np.diff(low_raw_db, prepend=low_raw_db[0]))
    low_db = 10 * np.log10(_smooth(np.maximum(low, 1e-5) ** 2, round(0.25 * fr_per_s)))
    chroma = librosa.feature.chroma_stft(S=S ** 2, sr=sr, hop_length=hop)
    n_env = min(len(oenv), S.shape[1])

    # --- downbeats (best effort, assumes 4/4) ---
    downbeat_phase, db_conf = 0, 0.0
    nb = len(bfr)
    beat_strength = np.array([float(oenv[min(b, len(oenv) - 1)]) for b in bfr]) if nb else np.zeros(0)
    if nb >= 8:
        def around(sig, b, w=2):
            return float(np.max(sig[max(0, b - w):min(len(sig), b + w + 1)]))
        lo = np.array([around(low_on, b) for b in bfr])
        on = np.array([around(oenv, b) for b in bfr])
        seg = np.split(np.arange(chroma.shape[1]), np.clip(bfr, 0, chroma.shape[1] - 1))
        cmeans = [chroma[:, s].mean(axis=1) if len(s) else np.zeros(12) for s in seg]
        cchg = np.zeros(nb)
        for i in range(nb):
            a_, b_ = cmeans[i], cmeans[i + 1] if i + 1 < len(cmeans) else cmeans[i]
            den = np.linalg.norm(a_) * np.linalg.norm(b_)
            cchg[i] = 1 - float(a_ @ b_ / den) if den > 1e-9 else 0.0
        score = _z(lo) + _z(cchg) + 0.5 * _z(on)
        ph = np.array([score[p::4].mean() for p in range(4)])
        downbeat_phase = int(np.argmax(ph))
        srt = np.sort(ph)
        db_conf = float((srt[-1] - srt[-2]) / (np.std(score) + 1e-9))

    # --- drops: biggest energy jumps landing on a beat ---
    win = cfg["drop_window_s"]
    drops = []
    if nb:
        lt = rms_t[:n_env]
        e_fine = 10 * np.log10(_smooth(pw, round(0.06 * fr_per_s)))
        low_fine = 10 * np.log10(_smooth(np.maximum(low, 1e-5) ** 2, round(0.06 * fr_per_s)))

        def jump_at(tb, w_pre, w_post, gap, eb, lb):
            pre = eb[(rms_t >= tb - w_pre) & (rms_t < tb - gap)]
            post = eb[(rms_t >= tb + 0.02) & (rms_t < tb + w_post)]
            lpre = lb[(lt >= tb - w_pre) & (lt < tb - gap)]
            lpost = lb[(lt >= tb + 0.02) & (lt < tb + w_post)]
            if len(pre) < 3 or len(post) < 3 or not len(lpre) or not len(lpost):
                return 0.0, 0.0, -99.0
            return (float(post.mean() - pre.mean()), float(lpost.mean() - lpre.mean()), float(post.mean()))

        # stage 1: long windows find drop regions; a drop = kick/bass returning, so the low-band
        # jump is weighted over broadband loudness
        jumps = np.array([jump_at(tb, win, win, 0.15, e_fast, low_db[:n_env]) for tb in beat_t_audio])
        loud = np.percentile(e_fast, 50)
        score = 0.4 * jumps[:, 0] + 0.6 * jumps[:, 1]
        cand = [i for i in range(nb) if score[i] >= cfg["drop_min_db"] and jumps[i, 0] >= 0
                and jumps[i, 2] >= loud]
        cand.sort(key=lambda i: -score[i])
        taken = []
        for i in cand:
            if all(abs(beat_t_audio[i] - beat_t_audio[j]) >= cfg["drop_min_separation_s"] for j in taken):
                taken.append(i)
        # stage 2: short windows pick the exact beat (within +-2 beats) where the energy hits
        for i in sorted(taken):
            best, best_s = i, -1e9
            for j in range(max(0, i - 2), min(nb, i + 3)):
                bj, lj, _ = jump_at(beat_t_audio[j], 0.45, 0.4, 0.03, e_fine, low_fine)
                s_ = 0.4 * bj + 0.6 * lj
                if s_ > best_s:
                    best, best_s = j, s_
            drops.append({"beat_index": int(best), "t_audio": float(beat_t_audio[best]),
                          "score": round(float(score[i]), 1), "jump_db": round(float(jumps[i, 0]), 1),
                          "bass_jump_db": round(float(jumps[i, 1]), 1)})

    # --- builds: sustained rise in slow energy before each drop ---
    builds = []
    step = 0.25
    for d in drops:
        tb = d["t_audio"]
        t_end = tb - 0.5
        if t_end <= 0:
            continue
        def E(t):
            return float(np.interp(t, rms_t, e_slow))
        t = t_end
        while t - step > max(0.0, tb - cfg["build_max_s"]) and E(t - step) <= E(t) + 0.3:
            t -= step
        rise = E(t_end) - E(t)
        if (t_end - t) >= cfg["build_min_s"] and rise >= cfg["build_min_rise_db"]:
            builds.append({"t_audio_start": float(t), "t_audio_end": float(tb), "rise_db": round(rise, 1)})

    # --- convert to video time / frames ---
    def vt(ta):
        return float(ta) + offset_s

    beats = []
    for i, ta in enumerate(beat_t_audio):
        t = vt(ta)
        beats.append({"t": round(t, 4), "frame": round(t * fps, 2),
                      "downbeat": bool(nb >= 8 and (i - downbeat_phase) % 4 == 0),
                      "strength": round(float(beat_strength[i]), 3) if nb else 0.0})
    drops_v = [{"t": round(vt(d["t_audio"]), 4), "frame": round(vt(d["t_audio"]) * fps, 2),
                "jump_db": d["jump_db"], "bass_jump_db": d["bass_jump_db"]} for d in drops]
    builds_v = [{"start_t": round(vt(b["t_audio_start"]), 3), "end_t": round(vt(b["t_audio_end"]), 3),
                 "start_frame": int(round(vt(b["t_audio_start"]) * fps)),
                 "end_frame": int(round(vt(b["t_audio_end"]) * fps)), "rise_db": b["rise_db"]}
                for b in builds]

    # per video frame series
    fidx = np.arange(n_frames)
    ta0 = fidx / fps - offset_s
    pf_rms = np.interp(ta0 + 0.5 / fps, rms_t, rms_db, left=np.nan, right=np.nan)
    pf_on = np.zeros(n_frames)
    i0s = np.searchsorted(env_t, ta0, side="left")
    i1s = np.searchsorted(env_t, ta0 + 1.0 / fps, side="left")
    for n in range(n_frames):
        if i1s[n] > i0s[n]:
            pf_on[n] = float(oenv[i0s[n]:i1s[n]].max())
    pf_beat = np.zeros(n_frames, dtype=np.int8)
    pf_down = np.zeros(n_frames, dtype=np.int8)
    for b in beats:
        k = int(round(b["frame"]))
        if 0 <= k < n_frames:
            pf_beat[k] = 1
            if b["downbeat"]:
                pf_down[k] = 1

    log(f"audio: {bpm:.1f} BPM ({len(beats)} beats, downbeat phase {downbeat_phase}, "
        f"conf {db_conf:.2f}), {len(onset_t_audio)} onsets, {len(drops_v)} drops, {len(builds_v)} builds")
    return {
        "available": True, "sr": sr, "hop": hop, "duration_s": round(dur, 3), "offset_s": offset_s,
        "bpm": round(bpm, 2), "bpm_librosa": round(tempo_lib, 2),
        "beat_period_frames": round(fps * 60.0 / bpm, 3) if bpm > 0 else None,
        "downbeat_phase": downbeat_phase, "downbeat_confidence": round(db_conf, 2),
        "beats": beats,
        "onsets": [round(vt(t), 4) for t in onset_t_audio],
        "drops": drops_v, "builds": builds_v,
        "energy_curve": {"t": [round(vt(t), 3) for t in rms_t[::4]],
                         "db": [round(float(x), 2) for x in e_fast[::4]]},
        "per_frame": {"rms_db": pf_rms, "onset": pf_on, "beat": pf_beat, "downbeat": pf_down},
    }
