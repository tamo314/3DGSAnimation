#!/usr/bin/env python3
"""viewpoints.json(元カメラ基準のビューア座標)を、T3形式(Blender世界座標、キャラ足元が原点)の
camera_paths JSON に変換する(独自実装)。

ビューア座標: X右・Y上・Z後方(元カメラは [0, 視点高, 0] で -Z を向く)。
Blender座標 : X右・Y前方・Z上、キャラの足元が原点、地面 z=0。
キャラ位置は元カメラの前方 --char-y メートル(ビューア座標 z=-char_y)に置く。
  Blender = (x, -z - char_y, y)
"""
import argparse
import json
import math

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="scripts/background/viewpoints.json")
ap.add_argument("--out", default="scripts/background/camera_paths_background.json")
ap.add_argument("--char-y", type=float, default=3.5)
a = ap.parse_args()

src = json.load(open(a.src, encoding="utf-8"))
labels = {"1_front_wide": "front_wide", "2_char_mid": "character_medium", "3_dapple_low": "dappled_low",
          "4_side_depth": "side_depth", "5_high_overview": "high_oblique"}


def conv(p):
    x, y, z = p
    return [round(x, 3), round(-z - a.char_y, 3), round(y, 3)]


cams = []
for v in src["viewpoints"]:
    f = 13.5 / math.tan(math.radians(v["fov"]) / 2)  # 4:3, センサー幅36mm → 高さ27mm、縦FOVから焦点距離
    cams.append({"name": labels[v["name"]], "position": conv(v["pos"]), "target": conv(v["target"]),
                 "focal_length_mm": round(f, 1), "roll_deg": 0.0})
out = {
    "_comment": "背景(forest1由来のWorld Labs世界)で破綻なく見られることを確認した5視点。T3の仮定義(scripts/gaussian/camera_paths.json)は"
                "この世界では視点が木や岩の内側に入るため、世界の自由空間に合わせて詰め直した。座標はBlender世界座標(X右・Y前方・Z上、m)。",
    "version": "0.2-background-fit",
    "alignment": {"character_foot": [0.0, 0.0, 0.0], "source_camera": [0.0, -a.char_y, "視点高(world_meta.json の eye_height_m)"],
                  "character_facing": [0.0, -1.0, 0.0]},
    "cameras": cams,
}
json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(cams, ensure_ascii=False))
