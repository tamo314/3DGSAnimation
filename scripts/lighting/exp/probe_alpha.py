import bpy, numpy as np, os
sc = bpy.context.scene
sc.render.film_transparent = True
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1440, 1080
for o in bpy.data.objects:
    if o.name.startswith("background"):
        o.hide_render = True; o.hide_viewport = True
sc.camera = bpy.data.objects["high_oblique"]
sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = os.path.abspath("experiments/T5/_probe.png")
bpy.ops.render.render(write_still=True)
im = bpy.data.images.load(sc.render.filepath)
px = np.array(im.pixels[:]).reshape(1080, 1440, 4)
a = px[..., 3]
print("PROBE alpha>0 px", (a > 0).sum(), "alpha==1", (a > 0.99).sum(), "0<a<0.99", ((a > 0.01) & (a < 0.99)).sum())
sub = a[540:800, 700:860]
print("PROBE crop alpha mean over >0.01:", sub[sub > 0.01].mean())
for m in bpy.data.materials:
    if hasattr(m, "surface_render_method"):
        print("PROBE mat", m.name, m.surface_render_method, getattr(m, "blend_method", None))
