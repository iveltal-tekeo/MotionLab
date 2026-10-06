"""Negative self-test: realistic camera behaviour and NO edit effects (only plain cuts).

Handheld wobble + tremor, slow optical-style zoom, slow camera roll, lighting drift, film grain, a fast
(but normal) pan. A good detector reports the cuts and nothing else here.
"""
from __future__ import annotations

FPS, W, H = 30, 1280, 720


def plate_input(plates, name):
    return ["-loop", "1", "-framerate", str(FPS), "-i", str(plates / name)]


def segments(plates):
    T = []
    grain = "noise=alls=10:allf=t"
    # N1 handheld: smooth wander + small tremor + breathing exposure
    wx = "300+60*sin(n/23)+25*sin(n/9.1)+3*sin(n*1.7)"
    wy = "180+35*sin(n/31)+15*sin(n/7.3)+2*sin(n*2.3)"
    T.append({"name": "N1", "n": 150, "inputs": plate_input(plates, "p6_life.png"),
              "graph": f"[0:v]crop=1920:1080:x='{wx}':y='{wy}',scale={W}:{H}:flags=lanczos,format=yuv444p,"
                       f"trim=end_frame=150,setpts=N/(30*TB),eq=brightness='0.04*sin(n/20)':eval=frame,{grain}[v]",
              "gt": []})
    T.append(("cut",))
    # N2 slow lens zoom-in (x1.0 -> x1.18 over 150 frames) with gentle drift
    T.append({"name": "N2", "n": 150, "inputs": plate_input(plates, "p1_mandel.png"),
              "graph": "[0:v]crop=1920:1080:x='300+n*0.6':y='200+n*0.3',scale=1280:720:flags=lanczos,format=yuv444p,"
                       "trim=end_frame=150,setpts=N/(30*TB),zoompan=z='1+0.0012*in':d=1:s=1280x720:fps=30:"
                       f"x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2',{grain}[v]",
              "gt": []})
    T.append(("cut",))
    # N3 slow camera roll (+-3 degrees) on a textured plate
    T.append({"name": "N3", "n": 150, "inputs": plate_input(plates, "p4_sierp.png"),
              "graph": "[0:v]crop=1920:1080:x='200+n*1.2':y='150+n*0.5',scale=2000:1125:flags=lanczos,"
                       "rotate=a='0.05*sin(n/25)':ow=1280:oh=720:c=black,format=yuv444p,trim=end_frame=150,"
                       f"setpts=N/(30*TB),{grain}[v]",
              "gt": []})
    T.append(("cut",))
    # N4 a brisk but normal camera pan (1.3% of the width per frame, constant) + lighting drift
    T.append({"name": "N4", "n": 120, "inputs": plate_input(plates, "p9_wide_mandel.png"),
              "graph": "[0:v]crop=1920:1080:x='100+25*n':y='150',scale=1280:720:flags=lanczos,format=yuv444p,"
                       "trim=end_frame=120,setpts=N/(30*TB),eq=brightness='-0.05+0.1*n/120':eval=frame,"
                       f"{grain}[v]",
              "gt": []})
    return T
