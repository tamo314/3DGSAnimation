"""5視点レンダーを1枚のコンタクトシートにまとめる(Pillow)。
  python scripts/blender/contact_sheet.py <out_dir> <tag> <出力jpg>
"""
import os
import sys

from PIL import Image, ImageDraw

NAMES = ["front_wide", "character_medium", "dappled_low", "side_depth", "high_oblique"]


def main(out_dir, tag, dst, w=720):
    tiles = []
    for n in NAMES:
        p = os.path.join(out_dir, f"{tag}{n}_0001_composite.png")
        im = Image.open(p).convert("RGB")
        im = im.resize((w, int(im.height * w / im.width)))
        ImageDraw.Draw(im).text((8, 6), n, fill=(255, 255, 255))
        tiles.append(im)
    h = tiles[0].height
    sheet = Image.new("RGB", (w * 2, h * 3), (20, 20, 20))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 2) * w, (i // 2) * h))
    sheet.save(dst, quality=88)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
