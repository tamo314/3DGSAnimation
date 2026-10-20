"""T8: Tripoキャラの部位ごとのテクスチャ密度(texel/mm)を測る。 blender -b --python texel_density.py (GLBは固定パス)
三角形ごとに sqrt(UV面積 × テクスチャ辺² / 3D面積) をとり、部位(高さz)別に面積重み付きの中央値を出す。"""
import bpy, numpy as np, json
glb = r"C:/Work/3DGSAnimation/assets/generated/character/normalized/girl_healer.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
res = {}
texsz = None
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    for m in o.material_slots:
        for n in (m.material.node_tree.nodes if m.material and m.material.use_nodes else []):
            if n.type == "TEX_IMAGE" and n.image and texsz is None:
                texsz = list(n.image.size)
    me = o.data
    me.calc_loop_triangles()
    uv = me.uv_layers.active.data
    mw = np.array(o.matrix_world)
    vs = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", vs); vs = vs.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    uvs = np.empty(len(uv) * 2); uv.foreach_get("uv", uvs); uvs = uvs.reshape(-1, 2)
    lt = me.loop_triangles
    tv = np.array([t.vertices for t in lt]); tl = np.array([t.loops for t in lt])
    a3 = 0.5 * np.linalg.norm(np.cross(vs[tv[:, 1]] - vs[tv[:, 0]], vs[tv[:, 2]] - vs[tv[:, 0]]), axis=1)
    e1, e2 = uvs[tl[:, 1]] - uvs[tl[:, 0]], uvs[tl[:, 2]] - uvs[tl[:, 0]]
    a2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    z = vs[tv].mean(1)[:, 2]
    ok = a3 > 1e-10
    dens = np.sqrt(a2[ok] / a3[ok]) * (texsz[0] if texsz else 4096) / 1000.0   # texel/mm
    z, a3 = z[ok], a3[ok]
    for name, lo, hi in (("頭(z>0.9)", 0.9, 9), ("胴(0.5-0.9)", 0.5, 0.9), ("脚(<0.5)", -1, 0.5)):
        m_ = (z >= lo) & (z < hi)
        res.setdefault(name, []).append((dens[m_], a3[m_]))
print("TEXSZ", texsz)
out = {}
for k, lst in res.items():
    d = np.concatenate([x[0] for x in lst]); w = np.concatenate([x[1] for x in lst])
    i = np.argsort(d); cw = np.cumsum(w[i]) / w.sum()
    out[k] = {"median_texel_per_mm": float(d[i][np.searchsorted(cw, 0.5)]), "p10": float(d[i][np.searchsorted(cw, 0.1)]), "p90": float(d[i][np.searchsorted(cw, 0.9)]), "area_m2": float(w.sum())}
print("DENSITY", json.dumps(out, ensure_ascii=False))
