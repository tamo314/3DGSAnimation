"""光芒（god rays）の画像上の向きを、構造テンソルで推定する。

使い方: python estimate_shafts.py <forest.png> x0 y0 x1 y1
領域内の輝度を帯域通過（大きなボケ - さらに大きなボケ）し、勾配の構造テンソルの
主方向から「光芒の走る向き」を求める。垂直からの傾き（右上→左下を負）を度で返す。
"""
import sys
import numpy as np
from PIL import Image, ImageFilter


def luminance(path):
    im = Image.open(path).convert("L")
    return im


def band(im, s1, s2):
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(s1)), dtype=np.float32)
    b = np.asarray(im.filter(ImageFilter.GaussianBlur(s2)), dtype=np.float32)
    return a - b


def shaft_angle(path, box, s1=6, s2=40):
    im = luminance(path)
    f = band(im, s1, s2)
    x0, y0, x1, y1 = box
    f = f[y0:y1, x0:x1]
    gy, gx = np.gradient(f)
    jxx, jyy, jxy = (gx * gx).sum(), (gy * gy).sum(), (gx * gy).sum()
    # 勾配が最大の向き（光芒に直交）
    theta_grad = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    # 光芒の向き = 勾配に直交。画像座標 (x右, y下) での方向ベクトル
    dx, dy = -np.sin(theta_grad), np.cos(theta_grad)
    if dy < 0:
        dx, dy = -dx, -dy
    ang_from_vertical = np.degrees(np.arctan2(dx, dy))  # 負=下に行くほど左へ
    coherence = np.sqrt((jxx - jyy) ** 2 + 4 * jxy**2) / (jxx + jyy)
    return ang_from_vertical, coherence


if __name__ == "__main__":
    p = sys.argv[1]
    box = tuple(int(v) for v in sys.argv[2:6])
    a, c = shaft_angle(p, box)
    print(f"angle_from_vertical_deg={a:.1f} coherence={c:.2f}")
