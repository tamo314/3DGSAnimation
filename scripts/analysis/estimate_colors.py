"""日向/日陰の色比と空の色を、forest 画像の路面・空から測る（numpy + PIL のみ）。

出力: 各領域の平均 sRGB、線形RGB、色度 xy、相関色温度（McCamy 近似）。
日向と日陰の線形RGBの差 (lit - shade) は、同じ素材に対する「太陽直射光の寄与」の色。
"""
import json
import sys
import numpy as np
from PIL import Image


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb8(l):
    l = np.clip(np.asarray(l, dtype=np.float64), 0, 1)
    c = np.where(l <= 0.0031308, 12.92 * l, 1.055 * l ** (1 / 2.4) - 0.055)
    return np.round(c * 255).astype(int)


M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])


def xy_cct(lin):
    X, Y, Z = M @ lin
    s = X + Y + Z
    x, y = X / s, Y / s
    n = (x - 0.3320) / (0.1858 - y)
    cct = 449 * n**3 + 3525 * n**2 + 6823.3 * n + 5520.33
    return x, y, cct


def otsu(v, bins=128):
    h, e = np.histogram(v, bins=bins)
    h = h.astype(float)
    p = h / h.sum()
    c = (e[:-1] + e[1:]) / 2
    w = np.cumsum(p)
    m = np.cumsum(p * c)
    mt = m[-1]
    sb = (mt * w - m) ** 2 / (w * (1 - w) + 1e-12)
    return c[np.argmax(sb)]


def region(img, box):
    x0, y0, x1, y1 = box
    return img[y0:y1, x0:x1].reshape(-1, 3)


def summarize(lin):
    m = lin if lin.ndim == 1 else lin.mean(axis=0)
    x, y, cct = xy_cct(m)
    return {
        "srgb": lin_to_srgb8(m).tolist(),
        "linear": [round(float(v), 4) for v in m],
        "xy": [round(float(x), 4), round(float(y), 4)],
        "cct_K": int(round(cct)),
    }


def soil_mask(px):
    r, g, b = px[:, 0].astype(int), px[:, 1].astype(int), px[:, 2].astype(int)
    return (r > g) & (g > b) & (r - b > 20) & (g > 0.55 * r)  # 橙〜茶の土。緑・青・灰を除く


def main(path, tag):
    img = np.asarray(Image.open(path).convert("RGB"))
    out = {"image": tag}
    # 路面（手前の小道）。forest1 前提の固定ボックス。
    boxes = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    path_box = boxes.get("path", [780, 790, 1010, 1080])
    px = region(img, path_box)
    px = px[soil_mask(px)]
    lum = srgb_to_lin(px) @ np.array([0.2126, 0.7152, 0.0722])
    t = otsu(lum)
    lit = srgb_to_lin(px[lum > t])
    shade = srgb_to_lin(px[lum <= t])
    # 外れ値を避けるため各クラスは中央付近 60% の平均
    def trimmed(l):
        y = l @ np.array([0.2126, 0.7152, 0.0722])
        lo, hi = np.percentile(y, [20, 80])
        return l[(y >= lo) & (y <= hi)]
    lit_t, shade_t = trimmed(lit), trimmed(shade)
    out["soil_pixels"] = int(len(px))
    out["soil_lit_fraction"] = round(float(len(lit) / len(px)), 3)
    out["soil_lit"] = summarize(lit_t)
    out["soil_shade"] = summarize(shade_t)
    ml, ms = lit_t.mean(axis=0), shade_t.mean(axis=0)
    out["lit_over_shade_linear_rgb"] = [round(float(v), 3) for v in ml / ms]
    d = np.clip(ml - ms, 1e-6, None)
    out["sun_contribution_on_soil"] = summarize(d)  # 直射光 × 路面反射率
    # 太陽/空の相対色（路面反射率は消える）: (lit-shade)/shade
    rel = d / ms
    out["sun_over_sky_rgb_ratio_normalized_to_G"] = [round(float(v), 3) for v in rel / rel[1]]
    out["sun_to_sky_luminance_ratio_on_soil"] = round(float((d @ np.array([.2126, .7152, .0722])) / (ms @ np.array([.2126, .7152, .0722]))), 2)
    # 空（青空の抜け）
    sx0, sy0, sx1, sy1 = boxes.get("sky", [880, 0, 1130, 190])
    spx = region(img, [sx0, sy0, sx1, sy1])
    r, g, b = spx[:, 0].astype(int), spx[:, 1].astype(int), spx[:, 2].astype(int)
    sky = spx[(b > r + 25) & (b > g + 5) & (b > 150)]
    out["sky_pixels"] = int(len(sky))
    if len(sky) > 50:
        out["sky"] = summarize(srgb_to_lin(sky))
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
