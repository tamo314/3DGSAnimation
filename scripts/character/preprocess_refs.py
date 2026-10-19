"""Tripo multiview 入力用に、キャラクター参照画像の背景を除去して統一フレームに揃える。

- 背景除去: rembg (birefnet-general, ローカルモデル)
- 縮尺は変えない（3視点の相対スケールを保つ）。全視点で同じ縦範囲・同じ画像サイズにそろえ、
  横方向だけ各視点のマスク中心に合わせる。
- 出力: <out>/{front,left,back}.png (RGBA, 背景透過) と preprocess_report.json

使い方:
  python scripts/character/preprocess_refs.py --ref-dir <assets/reference/character> --out <dir>
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import new_session, remove

# 参照画像の対応（目視で確認済み）: girl1=正面, girl2=左側面(顔が画像左向き), girl4=背面。
# girl3 / girl5 は斜め向きの補助画像で、マルチビュー入力には使わない。
VIEWS = {"front": "girl1.png", "left": "girl2.png", "back": "girl4.png"}
PAD = 40
ALPHA_CUT = 8


def cutout(img: Image.Image, session) -> Image.Image:
    out = remove(img.convert("RGB"), session=session, alpha_matting=False)
    arr = np.array(out)
    # 小さな浮きノイズを落とす
    arr[..., 3] = np.where(arr[..., 3] < ALPHA_CUT, 0, arr[..., 3])
    return Image.fromarray(arr, "RGBA")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="birefnet-general")
    args = ap.parse_args()

    ref_dir, out = Path(args.ref_dir), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    session = new_session(args.model)

    cut, boxes = {}, {}
    for view, name in VIEWS.items():
        im = cutout(Image.open(ref_dir / name), session)
        bbox = im.getchannel("A").point(lambda a: 255 if a > ALPHA_CUT else 0).getbbox()
        cut[view], boxes[view] = im, bbox

    # 全視点共通の縦範囲（頭頂〜足元）と、横幅の最大値で出力キャンバスを決める
    top = min(b[1] for b in boxes.values()) - PAD
    bottom = max(b[3] for b in boxes.values()) + PAD
    width = max(b[2] - b[0] for b in boxes.values()) + 2 * PAD
    height = bottom - top
    side = max(width, height)  # 正方形キャンバス（縮尺は変えない）

    report = {"model": args.model, "canvas": side, "views": {}}
    for view, im in cut.items():
        x0, _, x1, _ = boxes[view]
        cx = (x0 + x1) // 2
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        # 元画像座標 (cx - side/2, top - (side-height)/2) を左上にして貼り付け
        ox = cx - side // 2
        oy = top - (side - height) // 2
        canvas.paste(im, (-ox, -oy))
        canvas.save(out / f"{view}.png")
        report["views"][view] = {
            "source": VIEWS[view],
            "mask_bbox": list(boxes[view]),
            "crop_origin": [ox, oy],
        }
    (out / "preprocess_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
