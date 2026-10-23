"""T11: 連鎖顔アップから既知の窓を切り出し、1122x1402へ拡大した超解像用の入力を作る。
  python make_sr_inputs.py FACE_DIR OUT_DIR WIN_NAME x0 y0 w [--min -120 --max 120]   (窓の高さ = w*1402/1122)"""
import sys, glob, re, os
from PIL import Image
d, out, name, x0, y0, w = sys.argv[1], sys.argv[2], sys.argv[3], *map(int, sys.argv[4:7])
arg = lambda k, dflt: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else dflt
lo, hi = arg("--min", -120), arg("--max", 120)
h = round(w * 1402 / 1122); os.makedirs(out, exist_ok=True)
for f in sorted(glob.glob(f"{d}/face_az*.png")):
    az = int(re.search(r"az([+-]\d+)", f).group(1))
    if not lo <= az <= hi: continue
    Image.open(f).convert("RGB").crop((x0, y0, x0 + w, y0 + h)).resize((1122, 1402), Image.LANCZOS).save(f"{out}/in_{name}_az{az:+04d}.png")
print("ok", w, h)
