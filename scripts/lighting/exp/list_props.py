import bpy, sys, os
sys.path.insert(0, r"C:/Work/3DGSAnimation-T5/scripts/blender")
import spike_common as sc
sc.init_gpu(); sc.enable_kiri()
sp = bpy.context.scene.sna_dgs_scene_properties
for p in sp.bl_rna.properties:
    if p.identifier in ("rna_type","name"): continue
    try: v = getattr(sp, p.identifier)
    except Exception as e: v = "?"
    print("PROP", p.identifier, "|", p.name, "|", p.description[:90], "|", v)
