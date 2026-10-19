"""背景PLY(full_res)を統合シーンの世界座標(X右・Y前方・Z上、m。キャラ付近が原点)で読む共通関数。"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "gaussian"))
import spzply  # noqa: E402

BG = r"C:/Work/3DGSAnimation/assets/generated/background"


def load(variant="full_res", scale=1.0, spot=(0.0, 3.5)):
    meta = json.load(open(os.path.join(BG, "world_meta.json"), encoding="utf-8"))
    k0 = meta["coordinates"]["metric_scale_factor"]
    eye = meta["coordinates"]["ground_plane_offset"]
    cl = spzply.read_ply(os.path.join(BG, f"forest_clearing_{variant}.ply"), "RDF")
    p = cl.positions
    w = np.stack([p[:, 0], p[:, 2], -p[:, 1]], 1) * k0 * scale + np.array([-spot[0], -spot[1], eye]) * scale
    alpha = 1 / (1 + np.exp(-cl.alphas))
    rgb = np.clip(0.5 + 0.2820948 * cl.colors, 0, 1)
    return w, alpha, rgb, cl
