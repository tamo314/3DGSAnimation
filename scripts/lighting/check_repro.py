"""再現性の確認(マイルストーンテスト): 同じ設定で描き直した5視点が最終レンダーとピクセル一致するか。
  powershell -ExecutionPolicy Bypass -File scripts/blender/run_lighting.ps1 -Out experiments/T5/repro -Tag r_
  python scripts/lighting/check_repro.py [final_dir] [repro_dir]
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
final = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "experiments", "T5", "final")
repro = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "experiments", "T5", "repro")
ok = True
for n in ["front_wide", "character_medium", "dappled_low", "side_depth", "high_oblique"]:
    a = np.asarray(Image.open(os.path.join(final, n + ".png")).convert("RGB")).astype(int)
    b = np.asarray(Image.open(os.path.join(repro, f"r_{n}_0001_composite.png")).convert("RGB")).astype(int)
    d = np.abs(a - b)
    print(f"{n:17s} max diff {d.max()}  px diff>2: {(d.max(2) > 2).sum()}")
    ok &= d.max() <= 2
print("REPRO OK" if ok else "REPRO MISMATCH")
sys.exit(0 if ok else 1)
