#!/usr/bin/env python3
"""Vertical 1080x1920 teaser reels (YouTube Shorts / TikTok / Reels) cut from the same beats and narration."""
import argparse, json, os, sys
from pathlib import Path
import build

REEL_CSS = """
  #vcap{font-size:25px!important;padding:10px 20px 12px!important;border-radius:12px!important;max-width:90vw!important}
  #vhook{padding:64px 22px 24px!important;font-size:33px!important}
  #vcard{gap:12px!important}
  #vcard .k{font-size:20px!important}
  #vcard .t{font-size:44px!important;line-height:1.35}
  #vcard .d{font-size:22px!important;background:#d9a441;color:#0b353c;padding:8px 20px;border-radius:30px;font-weight:800!important}
  #vprog{height:5px!important}
  #vhl{border-width:3px!important}
  #vwm{font-size:14px!important;padding:6px 12px!important;gap:7px!important;left:16px!important;
       bottom:calc(var(--capb) + 78px)!important}
  #vcard .br{margin-top:14px!important;gap:8px!important}
  #vcard .nm{font-size:26px!important}
  #vcard .wa{font-size:19px!important;padding:6px 16px!important}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice-dir", required=True)
    ap.add_argument("--page")
    ap.add_argument("--out-dir", default=str(build.HERE / "out" / "reels"))
    ap.add_argument("--only", nargs="*", help="reel ids to build")
    ap.add_argument("--chromium", default=os.environ.get("CHROMIUM_PATH"))
    args = ap.parse_args()

    script = build.load_script()
    cfg = json.loads((build.HERE / "reels.json").read_text(encoding="utf-8"))
    work = build.HERE / "out" / "work-reels"
    work.mkdir(parents=True, exist_ok=True)
    page = build.fetch_page(work, args.page)
    wm, contact = build.brand_html(script)
    have = {int(f.stem[:2]) for f in Path(args.voice_dir).iterdir() if f.stem[:2].isdigit()}
    for r in cfg["reels"]:
        if args.only and r["id"] not in args.only:
            continue
        if not set(r["beats"]) <= have:
            print(f"skip {r['id']}: missing recordings {sorted(set(r['beats']) - have)}", file=sys.stderr)
            continue
        beats = [script["beats"][n - 1] for n in r["beats"]]
        narr = build.narration(script, beats, work, args.voice_dir)
        build.render(page, beats, narr, Path(args.out_dir) / f"{r['id']}.mp4", work,
                     size=(540, 960), dpr=2, css=REEL_CSS, chromium=args.chromium,
                     hook=r["hook"], outro_card=r.get("cta", cfg["cta"]) + contact, outro=3.5, watermark=wm,
                     cam_top=205, cam_bottom=150, cap_bottom=70, lead=0.5)


if __name__ == "__main__":
    main()
