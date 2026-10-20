"""T8: metrics.json 群から比較表(Markdown)を作る。 python t8_table.py <評価ディレクトリ...>  (各ディレクトリに metrics.json)"""
import json, os, sys
cols = ["psnr_roi", "ssim_roi", "lpips", "psnr_edge", "psnr_flat", "sharp_ratio_edge", "flat_noise_ratio", "sil_iou", "alpha_err_band"]
print("| 評価 | 種類 | 視点数 | " + " | ".join(cols) + " |")
print("|---|---|---|" + "---|" * len(cols))
for d in sys.argv[1:]:
    m = json.load(open(os.path.join(d, "metrics.json")))
    for t, v in m["summary"].items():
        print(f"| {os.path.basename(d.rstrip('/'))} | {t} | {v['n_views']} | " + " | ".join(f"{v[c]:.3f}" if c in ("ssim_roi", "lpips", "sharp_ratio_edge", "flat_noise_ratio", "sil_iou", "alpha_err_band") else f"{v[c]:.2f}" for c in cols) + " |")
