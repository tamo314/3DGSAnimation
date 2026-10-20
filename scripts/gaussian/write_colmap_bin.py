"""COLMAPテキスト(sparse/0/{cameras,images,points3D}.txt)を、公式3DGS系リーダーが期待するバイナリ(.bin)に変換する。
  python scripts/gaussian/write_colmap_bin.py experiments/T7/data/char_scene_black/sparse/0
PINHOLE(model_id=1)のみ対応。トラック情報は空。
"""
import struct
import sys
import os

d = sys.argv[1]
cams = []
for ln in open(os.path.join(d, "cameras.txt")):
    if ln.startswith("#") or not ln.strip():
        continue
    t = ln.split()
    assert t[1] == "PINHOLE", t[1]
    cams.append((int(t[0]), 1, int(t[2]), int(t[3]), [float(x) for x in t[4:8]]))
with open(os.path.join(d, "cameras.bin"), "wb") as f:
    f.write(struct.pack("<Q", len(cams)))
    for cid, mid, w, h, p in cams:
        f.write(struct.pack("<iiQQ", cid, mid, w, h))
        f.write(struct.pack("<4d", *p))

lines = [ln for ln in open(os.path.join(d, "images.txt")) if not ln.startswith("#")]
imgs = []
i = 0
while i < len(lines):
    if not lines[i].strip():
        i += 1
        continue
    t = lines[i].split()
    imgs.append((int(t[0]), [float(x) for x in t[1:5]], [float(x) for x in t[5:8]], int(t[8]), t[9]))
    i += 2
with open(os.path.join(d, "images.bin"), "wb") as f:
    f.write(struct.pack("<Q", len(imgs)))
    for iid, q, tv, cid, name in imgs:
        f.write(struct.pack("<i4d3di", iid, *q, *tv, cid))
        f.write(name.encode() + b"\x00")
        f.write(struct.pack("<Q", 0))

pts = []
for ln in open(os.path.join(d, "points3D.txt")):
    if ln.startswith("#") or not ln.strip():
        continue
    t = ln.split()
    pts.append((int(t[0]), [float(x) for x in t[1:4]], [int(x) for x in t[4:7]], float(t[7])))
with open(os.path.join(d, "points3D.bin"), "wb") as f:
    f.write(struct.pack("<Q", len(pts)))
    for pid, xyz, rgb, err in pts:
        f.write(struct.pack("<Q3d3Bd", pid, *xyz, *rgb, err))
        f.write(struct.pack("<Q", 0))
print("wrote bin:", len(cams), "cams,", len(imgs), "images,", len(pts), "points")
