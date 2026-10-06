"""Extended synthetic test: every effect family the main test does not cover (ffmpeg filters only).

    .venv\\Scripts\\python tools\\make_testvideo.py --extended   -> tools\\selftest\\synthetic_extended.mp4 + _truth.json

Effects: zoom punch in/out, shake, iris reveal, blur in/out, invert, saturation pop, colour flash, push/slide,
stepped frame repeat (on 2s), light leak, mirror, split screen, text, slice glitch, strobe, whip-pan transition,
dip to white, spin, speed ramp. Ground truth frame ranges are local to each segment and shifted to global
frames by the shared timeline joiner; repeats and transition blends are measured from the rendered pixels.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from motionlab.util import run, tool

FPS, W, H = 30, 1280, 720


def plate_input(plates, name):
    return ["-loop", "1", "-framerate", str(FPS), "-i", str(plates / name)]


def speed_sum_expr(speed_of_k: str) -> str:
    """x(n) = sum_{k=1..n} speed(k), as an ffmpeg expression (speed_of_k uses ld(1) as k)."""
    return f"(st(0,0);st(1,1);while(lte(ld(1),n),st(0,ld(0)+({speed_of_k}));st(1,ld(1)+1));ld(0))"


def pan(i, x, y, n_src, cw=1920, ch=1080, pw=2560, ph=1440, extra=""):
    return (f"[{i}:v]crop={cw}:{ch}:x='clip({x},0,{pw - cw})':y='clip({y},0,{ph - ch})',"
            f"scale={W}:{H}:flags=lanczos,format=yuv444p,trim=end_frame={n_src},setpts=N/(30*TB){extra}")


def make_assets(plates):
    """Wide plates for whip/speed ramp, a text overlay and a light-leak image."""
    p9 = plates / "p9_wide_mandel.png"
    if not p9.exists():
        run([tool("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i",
             "mandelbrot=s=5120x1440:start_scale=0.05:end_scale=0.05:start_x=-0.75:start_y=0.1:maxiter=250:"
             "inner=mincol:outer=normalized_iteration_count", "-frames:v", "1", str(p9)])
    p10 = plates / "p10_wide_grad.png"
    if not p10.exists():
        run([tool("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i",
             "gradients=s=5120x1440:n=7:seed=9:speed=0:c0=0x1b5e20:c1=0xfdd835:c2=0x6a1b9a:c3=0xff7043:"
             "c4=0x0277bd:c5=0xeceff1:c6=0x263238", "-frames:v", "1", "-vf",
             "format=rgb24,noise=alls=20:allf=u,drawgrid=w=128:h=96:t=2:c=white@0.35", str(p10)])
    txt = plates / "text_overlay.png"
    if not txt.exists():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        try:
            f = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 120)
        except OSError:
            f = ImageFont.load_default()
        msg = "MOTION LAB"
        tw = d.textlength(msg, font=f)
        d.text(((W - tw) / 2, 470), msg, font=f, fill=(255, 255, 255, 255), stroke_width=6,
               stroke_fill=(0, 0, 0, 255))
        im.save(txt)
    leak = plates / "leak.png"
    if not leak.exists():
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        g = np.exp(-((xx - 1000) ** 2 + (yy - 180) ** 2) / (2 * 420.0 ** 2))
        img = np.stack([255 * g, 150 * g, 40 * g], axis=-1).clip(0, 255).astype(np.uint8)
        Image.fromarray(img).save(leak)
    return p9, p10, txt, leak


def segments(plates):
    """Returns the timeline: dicts for segments, tuples for joins. Each segment: inputs, graph -> [v],
    n (output frames) and gt [(type, local_start, local_end, extra)]."""
    p9, p10, txt, leak = make_assets(plates)
    T = []

    # X1 zoom punch in at 30 (x1.25, held), punch out at 55
    T.append({"name": "X1", "n": 75, "inputs": plate_input(plates, "p1_mandel.png"),
              "graph": pan(0, "120+3*n", "60+n", 75) + ",zoompan=z='if(between(in,30,54),1.25,1)':d=1:"
                       f"s={W}x{H}:fps=30:x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2'[v]",
              "gt": [("zoom_in", 30, 30, {}), ("zoom_out", 55, 55, {})]})
    T.append(("cut",))
    # X2 post shake 30-41 (jitter added to a slow pan)
    jx = "if(between(n,30,41),34*sin(n*2.7)+18*sin(n*5.3),0)"
    jy = "if(between(n,30,41),22*cos(n*1.9)+12*sin(n*4.1),0)"
    T.append({"name": "X2", "n": 75, "inputs": plate_input(plates, "p4_sierp.png"),
              "graph": pan(0, f"50+2*n+{jx}", f"100+1.5*n+{jy}", 75) + "[v]",
              "gt": [("shake", 30, 41, {"tol": 1})]})
    T.append(("xfade", "circleopen", 15))
    # X3 blur in/out 30-40 (gaussian, no motion change)
    sig = [1, 2, 4, 6, 8, 8, 8, 6, 4, 2, 1]
    blur = "".join(f",gblur=sigma={s}:enable='eq(n,{30 + i})'" for i, s in enumerate(sig))
    T.append({"name": "X3", "n": 75, "inputs": plate_input(plates, "p5_spectrum.png"),
              "graph": pan(0, "600-3*n", "50+n", 75) + blur + "[v]", "gt": [("blur", 30, 40, {})]})
    T.append(("cut",))
    # X4 invert 30-35
    T.append({"name": "X4", "n": 75, "inputs": plate_input(plates, "p6_life.png"),
              "graph": pan(0, "200+2*n", "60+2*n", 75) + ",negate=enable='between(n,30,35)'[v]",
              "gt": [("invert", 30, 35, {})]})
    T.append(("cut",))
    # X5 black & white -> colour at 30 (saturation pop), red colour flash 50-52
    T.append({"name": "X5", "n": 75, "inputs": plate_input(plates, "p8_grad.png"),
              "graph": pan(0, "100+3*n", "150-0.6*n", 75) + ",hue=s=0:enable='lt(n,30)',"
                       "colorchannelmixer=rr=1:gg=0.3:bb=0.3:enable='between(n,50,52)'[v]",
              "gt": [("sat_pop", 30, 30, {}), ("flash_color", 50, 52, {})]})
    T.append(("xfade", "slideleft", 15))
    # X6 stepped frame repeat ("on 2s") 20-43
    T.append({"name": "X6", "n": 75, "inputs": plate_input(plates, "p6_life.png"),
              "graph": pan(0, "100+4*n", "60+2*n", 80) + ",split=3[a][b][c];"
                       "[a]trim=end_frame=20,setpts=PTS-STARTPTS[a1];"
                       "[b]trim=start_frame=20:end_frame=44,setpts=PTS-STARTPTS,select='not(mod(n,2))',"
                       "fps=30[b1];[c]trim=start_frame=44,setpts=PTS-STARTPTS[c1];"
                       "[a1][b1][c1]concat=n=3:v=1:a=0,setpts=N/(30*TB)[v]",
              "gt": [("frame_repeat", 20, 43, {"measure": "dups", "tol": 1})]})
    T.append(("cut",))
    # X7 light leak 21-43 (warm soft overlay, screen-blended with a triangle envelope)
    env = "if(between(N,21,43),1-abs(N-32)/12,0)"
    T.append({"name": "X7", "n": 75, "inputs": plate_input(plates, "p2_mandel.png") + ["-loop", "1", "-framerate",
                                                                                          "30", "-i", str(leak)],
              "graph": pan(0, "400-2*n", "200-n", 75) + ",format=gbrp[b];[1:v]format=gbrp[lk];"
                       f"[b][lk]blend=all_expr='A+(255-A)*B/255*{env}',format=yuv444p[v]",
              "gt": [("light_leak", 21, 43, {"tol": 2})]})
    T.append(("cut",))
    # X8 left/right mirror 20-59
    T.append({"name": "X8", "n": 75, "inputs": plate_input(plates, "p1_mandel.png"),
              "graph": pan(0, "300+3*n", "200+n", 75) + ",split[a][b];[b]crop=640:720:0:0,hflip[r];"
                       "[a][r]overlay=640:0:enable='between(n,20,59)'[v]",
              "gt": [("mirror", 20, 59, {})]})
    T.append(("cut",))
    # X9 split screen 30-69 (right half replaced by a different moving shot)
    T.append({"name": "X9", "n": 90, "inputs": plate_input(plates, "p4_sierp.png") + plate_input(plates, "p8_grad.png"),
              "graph": pan(0, "80+2*n", "50+1.5*n", 90) + "[m];" + pan(1, "500-3*n", "200+n", 90)
                       + ",crop=640:720:320:0[h];[m][h]overlay=640:0:enable='between(n,30,69)'[v]",
              "gt": [("split_screen", 30, 69, {})]})
    T.append(("cut",))
    # X10 text overlay 20-59
    T.append({"name": "X10", "n": 75, "inputs": plate_input(plates, "p8_grad.png") + ["-loop", "1", "-framerate",
                                                                                        "30", "-i", str(txt)],
              "graph": pan(0, "50+3*n", "300-n", 75) + "[b];[b][1:v]overlay=0:0:enable='between(n,20,59)',"
                       "format=yuv444p[v]",
              "gt": [("text", 20, 59, {"tol": 1})]})
    T.append(("cut",))
    # X11 slice glitch 30-33 (three horizontal bands displaced)
    en = "enable='between(n,30,33)'"
    T.append({"name": "X11", "n": 60, "inputs": plate_input(plates, "p1_mandel.png"),
              "graph": pan(0, "500+2*n", "100+2*n", 60) + ",split=4[a][b][c][d];[b]crop=1280:90:0:120[b1];"
                       "[c]crop=1280:60:0:380[c1];[d]crop=1280:70:0:560[d1];"
                       f"[a][b1]overlay=110:120:{en}[t1];[t1][c1]overlay=-150:380:{en}[t2];"
                       f"[t2][d1]overlay=80:560:{en}[v]",
              "gt": [("glitch", 30, 33, {})]})
    T.append(("cut",))
    # X12 strobe 30-37: every other frame black
    T.append({"name": "X12", "n": 60, "inputs": plate_input(plates, "p4_sierp.png"),
              "graph": pan(0, "300+2*n", "200+n", 60)
                       + ",drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(n,30,36)*not(mod(n,2))'[v]",
              "gt": [("strobe", 30, 36, {"tol": 1})]})
    T.append(("cut",))
    # X13 + X14 whip-pan transition: A accelerates to 31% of width per frame (blurred), cut, B decelerates
    tail = [60, 140, 260, 400, 560]
    sp_a = "if(lt(ld(1),70),3," + "".join(f"if(eq(ld(1),{70 + i}),{v}," for i, v in enumerate(tail)) + "3" + ")" * len(tail) + ")"
    blur_a = "".join(f",avgblur=sizeX={s}:sizeY=1:enable='eq(n,{70 + i})'" for i, s in enumerate([4, 10, 20, 32, 48]))
    T.append({"name": "X13", "n": 75, "inputs": plate_input(plates, p9.name),
              "graph": pan(0, f"100+{speed_sum_expr(sp_a)}", "200", 75, pw=5120) + blur_a + "[v]",
              "gt": [("whip_out", 70, 74, {})]})
    T.append(("cut",))
    head = [400, 260, 140, 60]
    sp_b = "".join(f"if(eq(ld(1),{1 + i}),{v}," for i, v in enumerate(head)) + "3" + ")" * len(head)
    blur_b = "".join(f",avgblur=sizeX={s}:sizeY=1:enable='eq(n,{i})'" for i, s in enumerate([48, 32, 20, 10, 4]))
    T.append({"name": "X14", "n": 60, "inputs": plate_input(plates, p10.name),
              "graph": pan(0, f"400+{speed_sum_expr(sp_b)}", "150", 60, pw=5120) + blur_b + "[v]",
              "gt": [("whip_in", 0, 4, {})]})
    T.append(("xfade", "fadewhite", 15))
    # X15 spin 30-41: 360 degrees in 12 steps of 30 (rotated from a 2x picture so corners stay covered)
    T.append({"name": "X15", "n": 75, "inputs": plate_input(plates, "p1_mandel.png"),
              "graph": pan(0, "200+2*n", "150+n", 75) + ",scale=2600:1462,"
                       "rotate=a='if(between(n,30,41),(n-29)*PI/6,0)':ow=1280:oh=720:c=black[v]",
              "gt": [("spin", 30, 41, {})]})
    T.append(("cut",))
    # X16 speed ramp: pan 12 px/f -> 2 px/f over 30-35, slow until 64, back to 12 px/f over 65-70
    sp_c = ("if(lt(ld(1),30),12,if(lt(ld(1),36),12-(ld(1)-29)*10/6,if(lt(ld(1),65),2,"
            "if(lt(ld(1),71),2+(ld(1)-64)*10/6,12))))")
    T.append({"name": "X16", "n": 105, "inputs": plate_input(plates, p9.name),
              "graph": pan(0, f"1500+{speed_sum_expr(sp_c)}", "100", 105, pw=5120) + "[v]",
              "gt": [("speed_ramp", 30, 36, {"tol": 4}), ("speed_ramp", 64, 71, {"tol": 4})]})
    return T


def render_segment(seg: dict, workdir, read_frames) -> tuple:
    out = workdir / f"seg_{seg['name']}.mkv"
    run([tool("ffmpeg"), "-y", "-v", "error", *seg["inputs"], "-filter_complex", seg["graph"], "-map", "[v]",
         "-frames:v", str(seg["n"]), "-c:v", "ffv1", "-pix_fmt", "yuv444p", str(out)])
    notes = []
    for typ, a, b, extra in seg["gt"]:
        if extra.get("measure") == "dups":
            fr = read_frames(out, 0, seg["n"] - 1)
            same = [t for t in range(1, seg["n"]) if np.abs(fr[t] - fr[t - 1]).mean() < 0.01]
            if same:
                a, b = min(same) - 1, max(same)
        notes.append((typ, a, b, {k: v for k, v in extra.items() if k != "measure"}))
    return out, notes
