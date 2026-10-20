"""Presenter-camera support: one face clip per beat, composited over the page recording.

- prep(): trims the silence at both ends of a clip (audio and picture together), evens out loudness
  and finds the face position with OpenCV so every clip is framed the same way.
- overlay_full(): round picture-in-picture in the top-left corner of the 16:9 lesson video.
- overlay_reel(): face filling the bottom of a 9:16 reel.
Face pictures are shown only while the presenter speaks; between beats the first/last frame is held.
"""
import json, re, subprocess
from pathlib import Path

import build

FF = build.FF
FPS = build.FPS


def _probe_silence(src):
    out = subprocess.run([FF, "-i", str(src), "-af", "silencedetect=n=-40dB:d=0.4", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    hh, mm, ss = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    dur = int(hh) * 3600 + int(mm) * 60 + float(ss)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    t0 = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    t1 = starts[-1] if starts and (len(ends) < len(starts) or ends[-1] > dur - 0.05) else dur
    return dur, max(0.0, t0 - 0.15), min(dur, t1 + 0.25)


def _face_box(src, t0, t1):
    """Median face box (x, y, w, h) in the upright video frame, from a handful of sampled frames."""
    import cv2
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    boxes = []
    for k in range(7):
        t = t0 + (t1 - t0) * (k + 0.5) / 7
        png = subprocess.run([FF, "-v", "error", "-ss", f"{t:.2f}", "-i", str(src), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
        img = cv2.imdecode(__import__("numpy").frombuffer(png, "uint8"), cv2.IMREAD_GRAYSCALE)
        h = img.shape[0]
        f = casc.detectMultiScale(img, 1.1, 6, minSize=(h // 10, h // 10))
        if len(f):
            boxes.append(max(f, key=lambda b: b[2] * b[3]))
    if not boxes:
        return None, img.shape[1], img.shape[0]
    med = lambda i: sorted(b[i] for b in boxes)[len(boxes) // 2]
    return (med(0), med(1), med(2), med(3)), img.shape[1], img.shape[0]


def prep(src, work):
    """-> dict(path=trimmed mp4, pcm=narration bytes, dur, box, W, H)."""
    work.mkdir(parents=True, exist_ok=True)
    key = f"{Path(src).name}-{Path(src).stat().st_size}"
    meta = work / f"{Path(src).stem}.json"
    out = work / f"{Path(src).stem}.mp4"
    if meta.exists() and json.loads(meta.read_text()).get("key") == key and out.exists():
        m = json.loads(meta.read_text())
    else:
        _, t0, t1 = _probe_silence(src)
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(src),
                        "-vf", f"fps={FPS}", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                        "-c:a", "aac", "-b:a", "192k", str(out)], check=True)
        box, W, H = _face_box(out, 0, t1 - t0)
        m = {"key": key, "box": [int(v) for v in box] if box is not None else None, "W": W, "H": H}
        meta.write_text(json.dumps(m))
    af = "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=200,loudnorm=I=-16:TP=-1.5:LRA=9"
    pcm = subprocess.run([FF, "-v", "error", "-i", str(out), "-af", af, "-f", "s16le", "-ac", "1",
                          "-ar", str(build.SR), "-"], check=True, capture_output=True).stdout
    return {**m, "path": out, "pcm": pcm, "dur": len(pcm) / 2 / build.SR}


def _crop(c, aspect, scale):
    """Crop rect around the face: width = scale * face width, given aspect (w/h); clamped to the frame."""
    W, H = c["W"], c["H"]
    if c["box"]:
        x, y, w, h = c["box"]
        cx, cy = x + w / 2, y + h * 0.62          # a little below the eyes: keeps beard and shoulders in
    else:
        cx, cy, w = W / 2, H * 0.45, W / 3
    cw = min(W, scale * w)
    ch = cw / aspect
    if ch > H:
        ch = H; cw = ch * aspect
    x0 = min(max(0, cx - cw / 2), W - cw)
    y0 = min(max(0, cy - ch / 2), H - ch)
    ev = lambda v: int(v) // 2 * 2
    return ev(cw), ev(ch), ev(x0), ev(y0)


def _track(clips, starts, lead, tail, aspect, scale, size, work, name):
    """One video stream: every clip cropped to `size`, padded with held frames, placed at its start time."""
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, c in enumerate(clips):
        cw, ch, x0, y0 = _crop(c, aspect, scale)
        p = work / f"{name}-{i:02d}.mp4"
        subprocess.run([FF, "-v", "error", "-y", "-i", str(c["path"]), "-an", "-vf",
                        f"crop={cw}:{ch}:{x0}:{y0},scale={size[0]}:{size[1]},setsar=1,fps={FPS},"
                        f"tpad=start_mode=clone:start_duration={lead}:stop_mode=clone:stop_duration={tail}",
                        "-c:v", "libx264", "-crf", "18", "-preset", "fast", str(p)], check=True)
        parts.append(p)
    lst = work / f"{name}.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    out = work / f"{name}.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)], check=True)
    return out


def overlay_full(base, clips, out, work, *, intro, lead, tail, d=330, margin=40):
    from PIL import Image, ImageDraw
    track = _track(clips, None, lead, tail, 1.0, 2.6, (d, d), work, "face-full")
    big = d * 4
    m = Image.new("L", (big, big), 0); ImageDraw.Draw(m).ellipse((0, 0, big - 1, big - 1), fill=255)
    m.resize((d, d), Image.LANCZOS).save(work / "mask.png")
    r = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(r).ellipse((0, 0, big - 1, big - 1), outline=(217, 164, 65, 255), width=28)
    r.resize((d, d), Image.LANCZOS).save(work / "ring.png")
    end = intro + sum(lead + c["dur"] + tail for c in clips)
    en = f"between(t,{intro},{end:.3f})"
    fc = (f"[1:v]format=rgba[f];[2:v]format=gray[m];[f][m]alphamerge[fm];"
          f"[0:v][fm]overlay={margin}:{margin}:enable='{en}'[v1];[v1][3:v]overlay={margin}:{margin}:enable='{en}'[v]")
    subprocess.run([FF, "-v", "error", "-y", "-i", str(base), "-itsoffset", str(intro), "-i", str(track),
                    "-loop", "1", "-i", str(work / "mask.png"), "-loop", "1", "-i", str(work / "ring.png"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "20",
                    "-preset", "medium", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)], check=True)


def overlay_reel(base, clips, out, work, *, lead, tail, fh=820, W=1080, H=1920):
    track = _track(clips, None, lead, tail, W / fh, 3.6, (W, fh), work, "face-reel")
    end = sum(lead + c["dur"] + tail for c in clips)
    fc = (f"[0:v][1:v]overlay=0:{H - fh}:enable='lte(t,{end:.3f})'[v1];"
          f"[v1]drawbox=x=0:y={H - fh - 6}:w={W}:h=6:color=0xd9a441:t=fill:enable='lte(t,{end:.3f})'[v]")
    subprocess.run([FF, "-v", "error", "-y", "-i", str(base), "-i", str(track), "-filter_complex", fc,
                    "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out)], check=True)
