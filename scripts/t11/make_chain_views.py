"""T11: 連鎖生成の切り抜き画像から views JSON(名目方位つき)を作る。
  python make_chain_views.py RGBA_DIR OUT.json [--min -130] [--max 180] [--prefix face_az] [--name c10_az]"""
import json, glob, re, sys
d, out = sys.argv[1], sys.argv[2]
arg = lambda k, dflt: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else dflt
lo, hi, pre, nm = int(arg("--min", -999)), int(arg("--max", 999)), arg("--prefix", "face_az"), arg("--name", "c10_az")
v = []
for f in sorted(glob.glob(f"{d}/{pre}*.png")):
    az = int(re.search(r"az([+-]\d+)", f).group(1))
    if lo <= az <= hi: v.append({"file": f.replace(chr(92), "/"), "az": az, "name": nm + "%+04d" % az})
json.dump(v, open(out, "w"), indent=1); print(len(v))
