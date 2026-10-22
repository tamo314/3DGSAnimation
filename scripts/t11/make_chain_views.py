"""T11: 連鎖生成の切り抜き画像から views JSON(名目方位つき)を作る。python make_chain_views.py RGBA_DIR OUT.json [--min -130] [--max 180]"""
import json, glob, re, sys
d, out = sys.argv[1], sys.argv[2]
lo = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else -999
hi = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 999
v = []
for f in sorted(glob.glob(d + "/face_az*.png")):
    az = int(re.search(r"az([+-]\d+)", f).group(1))
    if lo <= az <= hi: v.append({"file": f.replace(chr(92), "/"), "az": az, "name": "c10_az%+04d" % az})
json.dump(v, open(out, "w"), indent=1); print(len(v))
