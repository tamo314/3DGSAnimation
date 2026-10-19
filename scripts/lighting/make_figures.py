"""T5b/T6 の比較画像をまとめる(Pillow/numpy)。
  python scripts/lighting/make_figures.py   (experiments/T5/final と T4 の5視点、experiments/T5/out の no-bake 描画を使う)
出力(docs/img): 06-final-5views.jpg / 06-before-after.jpg / 06-char-closeup.jpg / 06-shadow-bake.jpg
"""
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FINAL = os.path.join(ROOT, "experiments", "T5", "final")
OUT = os.path.join(ROOT, "experiments", "T5", "out")
T4 = os.path.join(ROOT, "..", "3DGSAnimation-T4", "experiments", "T4", "headless")
IMG = os.path.join(ROOT, "docs", "img")
NAMES = ["front_wide", "character_medium", "dappled_low", "side_depth", "high_oblique"]


def load(p):
    return Image.open(p).convert("RGB")


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 7 * len(text), 16), fill=(0, 0, 0))
    d.text((4, 3), text, fill=(255, 255, 255))
    return im


def resize(im, w):
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)


def sheet5(w=720):
    tiles = [label(resize(load(os.path.join(FINAL, n + ".png")), w), n) for n in NAMES]
    h = tiles[0].height
    s = Image.new("RGB", (w * 2, h * 3), (20, 20, 20))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % 2) * w, (i // 2) * h))
    s.save(os.path.join(IMG, "06-final-5views.jpg"), quality=88)


def before_after(w=720):
    rows = []
    for n in NAMES:
        a = label(resize(load(os.path.join(T4, n + "_0001_composite.png")), w), n + " : T4 (before)")
        b = label(resize(load(os.path.join(FINAL, n + ".png")), w), n + " : T5b (after)")
        r = Image.new("RGB", (w * 2, a.height)); r.paste(a, (0, 0)); r.paste(b, (w, 0)); rows.append(r)
    s = Image.new("RGB", (w * 2, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        s.paste(r, (0, y)); y += r.height
    s.save(os.path.join(IMG, "06-before-after.jpg"), quality=86)


def crop_pair(name, box, scale, tag_a="T4", tag_b="T5b"):
    a = load(os.path.join(T4, name + "_0001_composite.png")).crop(box)
    b = load(os.path.join(FINAL, name + ".png")).crop(box)
    a = a.resize((int(a.width * scale), int(a.height * scale)), Image.LANCZOS)
    b = b.resize((int(b.width * scale), int(b.height * scale)), Image.LANCZOS)
    return label(a, f"{name} {tag_a}"), label(b, f"{name} {tag_b}")


def char_closeup():
    # 画像ごとに別々の画像として保存すると表示の偏りが出るため、before/after を縦に重ねる
    cols = []
    for name, box, sc in (("character_medium", (590, 270, 1050, 1000), 0.8), ("front_wide", (690, 430, 960, 800), 1.6),
                          ("high_oblique", (680, 520, 900, 800), 2.0)):
        a, b = crop_pair(name, box, sc)
        c = Image.new("RGB", (max(a.width, b.width), a.height + b.height + 4), (20, 20, 20))
        c.paste(a, (0, 0)); c.paste(b, (0, a.height + 4)); cols.append(c)
    H = max(c.height for c in cols)
    s = Image.new("RGB", (sum(c.width for c in cols) + 8 * (len(cols) - 1), H), (20, 20, 20))
    x = 0
    for c in cols:
        s.paste(c, (x, 0)); x += c.width + 8
    s.save(os.path.join(IMG, "06-char-closeup.jpg"), quality=90)


def shadow_bake():
    rows = []
    for name, box in (("front_wide", (560, 560, 1060, 960)), ("side_depth", (500, 560, 1000, 1000)), ("high_oblique", (560, 500, 1060, 940))):
        nb = load(os.path.join(OUT, f"nb2_{name}_0001_composite.png"))
        fb = load(os.path.join(FINAL, name + ".png"))
        d = (nb.convert("L").crop(box), fb.convert("L").crop(box))
        diff = np.clip((np.asarray(d[0], float) - np.asarray(d[1], float)) * 4 + 0, 0, 255).astype(np.uint8)   # 暗くなった量(強調)
        a = label(nb.crop(box), name + " : bake off")
        b = label(fb.crop(box), name + " : bake on")
        c = label(Image.fromarray(diff).convert("RGB"), "darkening x4")
        r = Image.new("RGB", (a.width * 3 + 8, a.height)); r.paste(a, (0, 0)); r.paste(b, (a.width + 4, 0)); r.paste(c, (2 * a.width + 8, 0))
        rows.append(r)
    s = Image.new("RGB", (rows[0].width, sum(r.height for r in rows) + 4 * (len(rows) - 1)), (20, 20, 20))
    y = 0
    for r in rows:
        s.paste(r, (0, y)); y += r.height + 4
    s.save(os.path.join(IMG, "06-shadow-bake.jpg"), quality=88)


if __name__ == "__main__":
    os.makedirs(IMG, exist_ok=True)
    sheet5(); before_after(); char_closeup(); shadow_bake()
    print("ok")
