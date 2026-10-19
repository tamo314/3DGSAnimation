#!/usr/bin/env python3
"""撮影した視点PNGを1枚のコンタクトシートにまとめる(独自実装)。
使い方: python contact_sheet.py SHOT_DIR OUT.png [--cols 3] [--width 640]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("shots")
ap.add_argument("out")
ap.add_argument("--cols", type=int, default=3)
ap.add_argument("--width", type=int, default=640)
a = ap.parse_args()

files = sorted(p for p in Path(a.shots).glob("*.png") if p.stem[0].isdigit())
ims = []
for f in files:
    im = Image.open(f).convert("RGB")
    im = im.resize((a.width, round(im.height * a.width / im.width)))
    ImageDraw.Draw(im).text((8, 6), f.stem, fill=(255, 255, 0))
    ims.append(im)
rows = -(-len(ims) // a.cols)
h = max(i.height for i in ims)
sheet = Image.new("RGB", (a.cols * a.width, rows * h), (20, 20, 20))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % a.cols) * a.width, (k // a.cols) * h))
sheet.save(a.out)
print(a.out, sheet.size)
