#!/usr/bin/env python3
"""Automated explainer video for module m1 (part 2) of the ops-training platform.

Pipeline:
  1. TTS: each beat in script.json -> audio/NN.mp3 + word timings (edge-tts).
     With --no-tts (or when TTS fails) durations are estimated and audio is silent.
  2. Playwright drives the real page: a virtual camera (zoom + pan), a highlight
     frame around the section being explained, and Arabic captions. Frames are
     captured deterministically so picture and voice stay in sync.
  3. ffmpeg assembles frames + narration into a 1920x1080 H.264 MP4.
"""
import argparse, asyncio, json, os, re, shutil, ssl, subprocess, sys, wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H, FPS = 1920, 1080, 30
MOVE = 0.7          # seconds of camera move before each beat's speech
TAIL = 0.3          # pause after each beat
INTRO = 2.5         # title card
OUTRO = 3.0         # closing card
SR = 48000
SOURCE_URL = "https://raw.githubusercontent.com/hatemattia1982-dot/-hatem-ops-training-/main/index.html"


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


FF = ffmpeg_exe()


# ---------------------------------------------------------------- TTS
async def tts_beat(text, voice, rate, out_mp3):
    import edge_tts
    import edge_tts.communicate as c
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if ca and os.path.exists(ca):  # edge-tts pins certifi; honour a custom CA (corporate proxies)
        c._SSL_CTX = ssl.create_default_context(cafile=ca)
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")  # edge-tts ignores env proxies
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary", proxy=proxy)
    words = []
    with open(out_mp3, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append([ch["offset"] / 1e7, ch["duration"] / 1e7, ch["text"]])
    return words


def mp3_to_pcm(mp3):
    raw = subprocess.run([FF, "-v", "error", "-i", str(mp3), "-f", "s16le", "-ac", "1",
                          "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return raw


def load_voice(path):
    """Recorded narration: trim leading/trailing silence, clean up rumble, even out loudness."""
    af = ("highpass=f=70,"
          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
          "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse,"
          "silenceremove=stop_periods=-1:stop_duration=0.7:stop_threshold=-45dB:stop_silence=0.45,"
          "acompressor=threshold=-20dB:ratio=2.5:attack=10:release=200,"
          "loudnorm=I=-16:TP=-1.5:LRA=9")
    return subprocess.run([FF, "-v", "error", "-i", str(path), "-af", af, "-f", "s16le", "-ac", "1",
                           "-ar", str(SR), "-"], check=True, capture_output=True).stdout


def estimate_seconds(text):
    return len(text.split()) / 2.35


# ---------------------------------------------------------------- captions
def caption_chunks(text, max_words=11):
    parts = [p.strip() for p in re.split(r"(?<=[.،؟?!:])\s+", text) if p.strip()]
    out = []
    for p in parts:
        ws = p.split()
        while len(ws) > max_words + 3:
            cut = max_words
            out.append(" ".join(ws[:cut]))
            ws = ws[cut:]
        if out and len(ws) <= 3 and len(out[-1].split()) + len(ws) <= max_words + 3 and not re.search(r"[.؟?!]$", out[-1]):
            out[-1] += " " + " ".join(ws)
        else:
            out.append(" ".join(ws))
    return out


def time_chunks(chunks, words, dur):
    """Return [(start, end, text)] relative to beat speech start."""
    n = sum(len(c.split()) for c in chunks)
    starts = []
    if words and abs(len(words) - n) <= max(2, n // 20):
        idx = 0
        for c in chunks:
            starts.append(words[min(idx, len(words) - 1)][0])
            idx += len(c.split())
    else:  # proportional to characters
        total = sum(len(c) for c in chunks)
        acc = 0
        for c in chunks:
            starts.append(dur * acc / total)
            acc += len(c)
    starts[0] = 0.0
    res = []
    for i, c in enumerate(chunks):
        end = starts[i + 1] if i + 1 < len(chunks) else dur + TAIL
        res.append((starts[i], end, c))
    return res


# ---------------------------------------------------------------- page driving
SETUP_JS = r"""
(cfg) => {
  document.body.classList.remove('locked');
  const st = document.createElement('style');
  st.textContent = `
    #gate,#appnav,#bar,#wm,#dash,#welcome,#npanel,#imodal,#gmodal{display:none!important}
    html,body{overflow:hidden!important;height:auto}
    html{background:#f5f0e8}
    #cam{position:fixed;top:0;left:0;width:100vw;transform-origin:0 0}
    #vhl{position:absolute;z-index:50;pointer-events:none;border:5px solid #d9a441;border-radius:14px;
         box-shadow:0 0 0 9999px rgba(10,30,34,.42),0 0 28px 6px rgba(217,164,65,.65)}
    .vmark{background:rgba(255,208,90,.75);border-radius:3px;box-shadow:0 0 0 3px rgba(255,208,90,.75);color:#0b353c;font-weight:700}
    #vcap{position:fixed;left:50%;bottom:var(--capb,44px);transform:translateX(-50%);max-width:82vw;width:max-content;z-index:100;
          direction:rtl;text-align:center;font:700 44px/1.55 'Tajawal','Cairo',sans-serif;color:#fff;
          background:rgba(8,26,30,.86);padding:16px 38px 20px;border-radius:18px;
          box-shadow:0 10px 30px rgba(0,0,0,.35);border-bottom:4px solid #d9a441}
    #vcap:empty{display:none}
    #vbadge{position:fixed;top:28px;right:34px;z-index:100;direction:rtl;display:flex;gap:12px;align-items:center;
            font:700 26px/1 'Tajawal',sans-serif}
    #vbadge .u{background:#0b353c;color:#fff;padding:12px 20px;border-radius:12px}
    #vbadge .s{background:#fff;color:#0b353c;padding:12px 20px;border-radius:12px;border:2px solid #d9a441;
               box-shadow:0 6px 18px rgba(0,0,0,.18)}
    #vprog{position:fixed;left:0;bottom:0;height:8px;background:#d9a441;z-index:100}
    #vcard{position:fixed;inset:0;z-index:200;display:none;align-items:center;justify-content:center;flex-direction:column;
           background:linear-gradient(160deg,#0b353c,#14545c 60%,#2b93a0);color:#fff;direction:rtl;text-align:center;gap:22px}
    #vcard .k{font:700 30px 'Tajawal';color:#d9a441;letter-spacing:2px}
    #vcard .t{font:800 84px 'Cairo','Tajawal';}
    #vcard .d{font:500 38px 'Tajawal';opacity:.92}
    #vhook{position:fixed;top:0;left:0;right:0;z-index:150;display:none;direction:rtl;text-align:center;
           padding:150px 60px 44px;background:linear-gradient(180deg,#0b353c 70%,rgba(11,53,60,0));color:#fff;
           font:800 60px/1.45 'Cairo','Tajawal',sans-serif}
    #vhook b{color:#f2c45c}
  `;
  document.head.appendChild(st);
  // wrap page content in a camera layer
  const cam = document.createElement('div'); cam.id = 'cam';
  while (document.body.firstChild) cam.appendChild(document.body.firstChild);
  document.body.appendChild(cam);
  const hl = document.createElement('div'); hl.id = 'vhl'; cam.appendChild(hl);
  for (const [id, html] of [['vcap',''],['vbadge',''],['vprog',''],['vcard',''],['vhook','']]) {
    const d = document.createElement('div'); d.id = id; d.innerHTML = html; document.body.appendChild(d);
  }
  document.getElementById('vbadge').innerHTML = `<span class="u">${cfg.badge}</span><span class="s"></span>`;
  window.scrollTo(0, 0);

  // ---- named targets inside module m1
  const m1 = document.getElementById('m1');
  const h3 = t => [...m1.querySelectorAll('h3')].find(h => h.textContent.includes(t));
  const nextTable = h => { let e = h.nextElementSibling; while (e && e.tagName !== 'TABLE') e = e.nextElementSibling; return e; };
  const kh = h3('ماذا يعرف'), ph = h3('الإدارة الوقائية');
  const kt = nextTable(kh), pt = nextTable(ph);
  const rows = t => [...t.querySelectorAll('tr')];
  const T = {head: [m1.querySelector('.mhead')], kh: [kh], kt: [kt], ph: [ph], pt: [pt],
             rule: [m1.querySelector('.box.rule')], mis: [m1.querySelector('.box.mis')],
             chk: [m1.querySelector('.box.chk')], scn: [m1.querySelector('.box.scn')]};
  for (let i = 1; i <= 4; i++) {
    T['kcol' + i] = rows(kt).map(r => r.children[i - 1]);
    T['prow' + i] = [rows(pt)[i]];
    T['mis' + i] = [T.mis[0].querySelectorAll('li')[i - 1]];
  }
  const sp = T.scn[0].querySelectorAll('p'); T.scn1 = [sp[0]]; T.scn2 = [sp[1]];
  window.__T = T;
}
"""

RECT_JS = r"""
(spec) => {
  const T = window.__T, cam = document.getElementById('cam');
  const prev = cam.style.transform; cam.style.transform = 'none';
  const u = rs => { const r = {l:1e9,t:1e9,r:-1e9,b:-1e9};
    for (const x of rs) { r.l = Math.min(r.l, x.left); r.t = Math.min(r.t, x.top); r.r = Math.max(r.r, x.right); r.b = Math.max(r.b, x.bottom); }
    return {x:r.l + scrollX, y:r.t + scrollY, w:r.r - r.l, h:r.b - r.t}; };
  const rectOf = key => u(T[key].map(e => e.getBoundingClientRect()));
  const phrase = (key, text) => {
    for (const el of T[key]) {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let full = '', nodes = [];
      while (walker.nextNode()) { nodes.push([walker.currentNode, full.length]); full += walker.currentNode.data; }
      const i = full.indexOf(text); if (i < 0) continue;
      const loc = pos => { for (let k = nodes.length - 1; k >= 0; k--) if (nodes[k][1] <= pos) return [nodes[k][0], pos - nodes[k][1]]; };
      const rg = document.createRange(); const a = loc(i), b = loc(i + text.length - 1);
      rg.setStart(a[0], a[1]); rg.setEnd(b[0], b[1] + 1);
      return rg;
    }
    return null;
  };
  const out = {cam: u(spec.cam.map(rectOf).map(r => ({left:r.x, top:r.y, right:r.x+r.w, bottom:r.y+r.h})))};
  document.querySelectorAll('.vmark').forEach(m => m.replaceWith(...m.childNodes));
  if (typeof spec.hl === 'string') out.hl = rectOf(spec.hl);
  else if (spec.hl) {
    const rg = phrase(spec.hl.in, spec.hl.text);
    if (rg) { out.hl = out.cam; out.mark = true; }  // frame the block, the phrase itself gets a marker
    else out.missing = spec.hl.text;
  }
  cam.style.transform = prev;
  return out;
}
"""

MARK_JS = r"""
(spec) => {
  document.querySelectorAll('.vmark').forEach(m => { const p = m.parentNode; m.replaceWith(...m.childNodes); p.normalize(); });
  if (!spec || typeof spec === 'string') return;
  for (const el of window.__T[spec.in]) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let full = '', nodes = [];
    while (walker.nextNode()) { nodes.push([walker.currentNode, full.length]); full += walker.currentNode.data; }
    const i = full.indexOf(spec.text); if (i < 0) continue;
    const loc = pos => { for (let k = nodes.length - 1; k >= 0; k--) if (nodes[k][1] <= pos) return [nodes[k][0], pos - nodes[k][1]]; };
    const rg = document.createRange(); const a = loc(i), b = loc(i + spec.text.length - 1);
    rg.setStart(a[0], a[1]); rg.setEnd(b[0], b[1] + 1);
    const span = document.createElement('span'); span.className = 'vmark';
    try { rg.surroundContents(span); } catch (e) { span.appendChild(rg.extractContents()); rg.insertNode(span); }
    return;
  }
}
"""

APPLY_JS = r"""
(s) => {
  document.getElementById('cam').style.transform = `translate(${-s.tx}px,${-s.ty}px) scale(${s.z})`;
  const hl = document.getElementById('vhl');
  if (s.hl) { Object.assign(hl.style, {display:'block', left:s.hl.x+'px', top:s.hl.y+'px', width:s.hl.w+'px', height:s.hl.h+'px', opacity:s.hlo}); }
  else hl.style.display = 'none';
  document.getElementById('vcap').textContent = s.cap || '';
  document.querySelector('#vbadge .s').textContent = s.label || '';
  document.getElementById('vbadge').style.display = s.label ? 'flex' : 'none';
  document.getElementById('vprog').style.width = (s.prog * 100) + '%';
  const card = document.getElementById('vcard');
  const hook = document.getElementById('vhook');
  if (s.hook) { hook.style.display = 'block'; hook.innerHTML = s.hook; } else hook.style.display = 'none';
  if (s.card) { card.style.display = 'flex'; card.style.opacity = s.cardo; card.innerHTML = s.card; } else card.style.display = 'none';
}
"""

CAP_SPACE = 250  # bottom band reserved for captions


def fetch_font(route):
    import urllib.request
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    ctx = ssl.create_default_context(cafile=ca) if ca and os.path.exists(ca) else None
    req = urllib.request.Request(route.request.url, headers={"User-Agent": route.request.headers.get("user-agent", "Mozilla/5.0")})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            route.fulfill(status=r.status, body=r.read(),
                          headers={"content-type": r.headers.get("content-type", ""), "access-control-allow-origin": "*"})
    except Exception as e:
        print("font fetch failed:", route.request.url[:80], e, file=sys.stderr)
        route.abort()


def camera_for(rect, max_zoom=1.75, top=90, bottom=CAP_SPACE):
    pad = 70 if W > H else 36
    rw, rh = rect["w"] + 2 * pad, rect["h"] + 2 * pad
    avail_h = H - bottom - top
    z = max(0.55, min(max_zoom, W / rw, avail_h / rh))
    cx, cy = rect["x"] + rect["w"] / 2, rect["y"] + rect["h"] / 2
    ty = cy * z - (top + avail_h / 2)
    # if the target is taller than the view, pin its top instead of its centre
    if rect["h"] * z > avail_h:
        ty = (rect["y"] - pad / 2) * z - top
    return {"z": z, "tx": cx * z - W / 2, "ty": ty}


def ease(t):
    return 0.5 - 0.5 * __import__("math").cos(__import__("math").pi * t)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rect(a, b, t):
    if a is None or b is None:
        return b if t >= 0.5 else a
    return {k: lerp(a[k], b[k], t) for k in ("x", "y", "w", "h")}


def fetch_page(work, page=None):
    if page:
        return page
    import urllib.request
    page = str(work / "index.html")
    ca = os.environ.get("SSL_CERT_FILE")
    ctx = ssl.create_default_context(cafile=ca) if ca and os.path.exists(ca) else None
    with urllib.request.urlopen(SOURCE_URL, context=ctx, timeout=60) as r:
        Path(page).write_bytes(r.read())
    return page


def narration(script, beats, work, voice_dir=None, no_tts=False):
    """Return [(pcm_bytes, dur, words)] per beat. words is None for recorded voice."""
    out = []
    use_tts = not no_tts and not voice_dir
    voice_files = {}
    if voice_dir:
        for f in sorted(Path(voice_dir).iterdir()):
            m = re.match(r"(\d+)", f.stem)
            if m and f.is_file():
                voice_files[int(m.group(1))] = f
        missing = [b["n"] for b in beats if b["n"] not in voice_files]
        if missing:
            sys.exit(f"missing recordings for beats: {missing}")
    (work / "audio").mkdir(parents=True, exist_ok=True)
    for b in beats:
        i = b["n"] - 1
        if voice_dir:
            data = load_voice(voice_files[b["n"]])
            out.append((data, len(data) / 2 / SR, None))
            print(f"beat {b['n']:02d}: {out[-1][1]:5.1f}s  {b['label']}  <- {voice_files[b['n']].name}")
            continue
        mp3 = work / "audio" / f"{i:02d}.mp3"
        wj = work / "audio" / f"{i:02d}.json"
        words = None
        if use_tts:
            key = json.dumps([b["text"], script["voice"], script["rate"]], ensure_ascii=False)
            if mp3.exists() and wj.exists() and json.loads(wj.read_text())["key"] == key:
                words = json.loads(wj.read_text())["words"]
            else:
                try:
                    words = asyncio.run(tts_beat(b["text"], script["voice"], script["rate"], mp3))
                    wj.write_text(json.dumps({"key": key, "words": words}, ensure_ascii=False))
                except Exception as e:
                    print(f"TTS failed ({type(e).__name__}: {e}); falling back to silent preview", file=sys.stderr)
                    use_tts = False
        if use_tts:
            data = mp3_to_pcm(mp3)
            dur = len(data) / 2 / SR
        else:
            dur = estimate_seconds(b["text"])
            data = b"\0\0" * int(dur * SR)
            words = []
        out.append((data, dur, words))
        print(f"beat {b['n']:02d}: {dur:5.1f}s  {b['label']}")
    return out


def render(page, beats, narr, out, work, *, size=(1920, 1080), badge="", chromium=None,
           intro_card=None, intro=INTRO, outro_card=None, outro=OUTRO, hook=None,
           cam_top=90, cam_bottom=CAP_SPACE, cap_bottom=44, lead=MOVE, dpr=1, css=""):
    """Drive the page and write an MP4 whose picture follows the narration beat by beat."""
    global W, H
    W, H = size
    frames = work / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir(parents=True)
    intro_t = intro if intro_card else 0.0
    total = intro_t + sum(lead + d + TAIL for _, d, _ in narr) + outro

    sil = lambda s: b"\0\0" * int(round(s * SR))
    track = [sil(intro_t)]
    for data, _, _ in narr:
        track += [sil(lead), data, sil(TAIL)]
    track.append(sil(outro))
    wav_path = work / "narration.wav"
    with wave.open(str(wav_path), "wb") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes(b"".join(track))

    from playwright.sync_api import sync_playwright
    concat = []
    n = [0]
    with sync_playwright() as p:
        launch = {"executable_path": chromium} if chromium else {}
        if os.environ.get("HTTPS_PROXY"):
            launch["proxy"] = {"server": os.environ["HTTPS_PROXY"], "bypass": "127.0.0.1,localhost"}
        br = p.chromium.launch(**launch)
        pg = br.new_page(viewport={"width": W, "height": H}, device_scale_factor=dpr)
        # deterministic render: no auth/analytics/embeds; fonts fetched via Python (honours custom CA)
        pg.route(re.compile(r"(gstatic\.com/firebasejs|youtube|googletagmanager|google-analytics)"),
                 lambda r: r.abort())
        pg.route(re.compile(r"https://fonts\.(googleapis|gstatic)\.com/.*"), fetch_font)
        url = page if re.match(r"https?://", page) else Path(page).resolve().as_uri()
        pg.goto(url, wait_until="load", timeout=90000)
        pg.wait_for_timeout(2500)
        pg.evaluate(SETUP_JS, {"badge": badge})
        pg.evaluate(f"document.documentElement.style.setProperty('--capb','{cap_bottom}px')")
        if css:
            pg.add_style_tag(content=css)
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(800)

        def snap(state, dur):
            f = frames / f"{n[0]:06d}.png"
            n[0] += 1
            pg.evaluate(APPLY_JS, state)
            pg.screenshot(path=str(f))
            concat.append((f, dur))

        elapsed = 0.0

        def base(cam_, hl, hlo, label, cap, extra=None):
            s = {**cam_, "hl": hl, "hlo": hlo, "label": "" if hook else label, "cap": cap,
                 "prog": elapsed / total, "hook": hook}
            if extra:
                s.update(extra)
            return s

        targets = []
        for b in beats:
            pg.evaluate(MARK_JS, None)
            r = pg.evaluate(RECT_JS, {"cam": b["cam"], "hl": b.get("hl")})
            if r.get("missing"):
                print("WARN phrase not found:", r["missing"], file=sys.stderr)
            hl = dict(r.get("hl") or r["cam"])
            hl = {"x": hl["x"] - 10, "y": hl["y"] - 8, "w": hl["w"] + 20, "h": hl["h"] + 16}
            targets.append((camera_for(r["cam"], top=cam_top, bottom=cam_bottom), hl))

        cam0 = targets[0][0]
        prev_cam, prev_hl = cam0, None
        if intro_card:
            snap(base(cam0, None, 0, "", "", {"card": intro_card, "cardo": 1}), intro_t - 0.5)
            elapsed += intro_t - 0.5
            steps = int(0.5 * FPS)
            for k in range(steps):
                snap(base(cam0, None, 0, "", "", {"card": intro_card, "cardo": 1 - (k + 1) / steps}), 1 / FPS)
                elapsed += 1 / FPS

        for b, (_, dur, words), (cam, hl) in zip(beats, narr, targets):
            pg.evaluate(MARK_JS, b.get("hl") if isinstance(b.get("hl"), dict) else None)
            steps = max(1, int(lead * FPS))
            same = prev_cam == cam
            for k in range(steps):
                t = ease((k + 1) / steps)
                c = cam if same else {q: lerp(prev_cam[q], cam[q], t) for q in cam}
                h = lerp_rect(prev_hl, hl, t) if prev_hl else hl
                snap(base(c, h, 1 if prev_hl else t, b["label"], ""), lead / steps)
                elapsed += lead / steps
            if words is None:  # recorded voice: show the beat's key points, split evenly
                ks = b.get("keys") or [b["label"]]
                caps = [(dur * k / len(ks), dur * (k + 1) / len(ks) + (TAIL if k == len(ks) - 1 else 0), t)
                        for k, t in enumerate(ks)]
            else:
                caps = time_chunks(caption_chunks(b["text"]), words, dur)
            for (s0, s1, txt) in caps:
                snap(base(cam, hl, 1, b["label"], txt), s1 - s0)
                elapsed += s1 - s0
            prev_cam, prev_hl = cam, hl

        pg.evaluate(MARK_JS, None)
        if outro_card:
            steps = int(0.6 * FPS)
            for k in range(steps):
                snap(base(prev_cam, prev_hl, 1, "", "", {"card": outro_card, "cardo": (k + 1) / steps,
                                                           "prog": 1, "hook": None}), 1 / FPS)
            snap(base(prev_cam, prev_hl, 1, "", "", {"card": outro_card, "cardo": 1, "prog": 1, "hook": None}),
                 outro - 0.6)
        br.close()

    lst = work / "frames.txt"
    with open(lst, "w") as f:
        for fp, d in concat:
            f.write(f"file '{fp}'\nduration {d:.5f}\n")
        f.write(f"file '{concat[-1][0]}'\n")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(wav_path),
           "-vf", f"fps={FPS},scale={W * dpr}:{H * dpr},format=yuv420p", "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-tune", "stillimage", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
           "-shortest", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print(f"wrote {out}  ({total:.1f}s = {total/60:.2f} min)")
    return total


def load_script():
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    for k, b in enumerate(script["beats"]):
        b["n"] = k + 1
    return script


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=None,
                    help="local path or site URL of the platform page (default: download SOURCE_URL)")
    ap.add_argument("--out", default=str(HERE / "out" / "m1-part2.mp4"))
    ap.add_argument("--no-tts", action="store_true", help="silent preview with estimated timing")
    ap.add_argument("--voice-dir", help="folder of recorded narration, one file per beat named 01, 02, ... "
                    "(any audio format); captions then show each beat's key points")
    ap.add_argument("--chromium", default=os.environ.get("CHROMIUM_PATH"))
    args = ap.parse_args()

    script = load_script()
    beats = script["beats"]
    work = HERE / "out" / "work"
    work.mkdir(parents=True, exist_ok=True)
    page = fetch_page(work, args.page)
    narr = narration(script, beats, work, args.voice_dir, args.no_tts)
    intro = (f"<div class='k'>{script['badge']}</div><div class='t'>{script['title']}</div>"
             "<div class='d'>ماذا يعرف؟ ماذا يراجع؟ ماذا يكتشف؟ ماذا يرفع؟</div>")
    outro = ("<div class='k'>نهاية الجزء الثاني</div><div class='t'>المشكلة التي تتكرر مرتين<br>مشكلة نظام</div>"
             "<div class='d'>نلقاك في الوحدة الثانية</div>")
    render(page, beats, narr, args.out, work, badge=script["badge"], chromium=args.chromium,
           intro_card=intro, outro_card=outro)


if __name__ == "__main__":
    main()
