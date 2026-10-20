"""T8: GLBに埋め込まれたテクスチャ(色・法線・ORM)を取り出して PNG で保存する。
  python scripts/character/extract_glb_textures.py <glb> <出力フォルダ>
GLBのJSONチャンクからマテリアルの参照を辿り、役割名(basecolor/normal/orm/emissive)で保存する。"""
import json, os, struct, sys
glb, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
data = open(glb, "rb").read()
magic, ver, total = struct.unpack("<III", data[:12])
assert magic == 0x46546C67
off, js, bin_ = 12, None, None
while off < total:
    ln, ty = struct.unpack("<II", data[off:off + 8])
    chunk = data[off + 8: off + 8 + ln]
    if ty == 0x4E4F534A: js = json.loads(chunk)
    elif ty == 0x004E4942: bin_ = chunk
    off += 8 + ln
roles = {}
for m in js["materials"]:
    p = m.get("pbrMetallicRoughness", {})
    for role, ref in (("basecolor", p.get("baseColorTexture")), ("orm", p.get("metallicRoughnessTexture")),
                      ("normal", m.get("normalTexture")), ("emissive", m.get("emissiveTexture")), ("occlusion", m.get("occlusionTexture"))):
        if ref is not None:
            roles.setdefault(role, set()).add(js["textures"][ref["index"]]["source"])
print("materials", len(js["materials"]), "images", len(js["images"]), {k: sorted(v) for k, v in roles.items()})
for role, idxs in roles.items():
    for i in sorted(idxs):
        img = js["images"][i]
        bv = js["bufferViews"][img["bufferView"]]
        raw = bin_[bv.get("byteOffset", 0): bv.get("byteOffset", 0) + bv["byteLength"]]
        ext = "png" if "png" in img.get("mimeType", "png") else "jpg"
        path = os.path.join(out, f"{role}_{i}.{ext}")
        open(path, "wb").write(raw)
        print("wrote", path, len(raw))
