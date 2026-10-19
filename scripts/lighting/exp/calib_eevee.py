import bpy, math, numpy as np, os
sc = bpy.context.scene
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
sc.render.engine = "BLENDER_EEVEE"; sc.render.resolution_x = 64; sc.render.resolution_y = 64
sc.view_settings.view_transform = "Standard"; sc.render.image_settings.file_format = "PNG"
bpy.ops.mesh.primitive_plane_add(size=10)
pl = bpy.context.active_object
m = bpy.data.materials.new("w"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1,1,1,1)
m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
m.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.0
pl.data.materials.append(m)
cd = bpy.data.cameras.new("c"); cd.type = "ORTHO"; cd.ortho_scale = 2
cam = bpy.data.objects.new("c", cd); sc.collection.objects.link(cam); cam.location = (0,0,5); sc.camera = cam
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True
bgn = w.node_tree.nodes["Background"]
def lin_pix(path):
    im = bpy.data.images.load(path); px = np.array(im.pixels[:]).reshape(-1,4)[:, :3].mean(0)
    bpy.data.images.remove(im); return px
def go(sun_s, el, wstr):
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]: bpy.data.objects.remove(o)
    if sun_s > 0:
        ld = bpy.data.lights.new("s", "SUN"); ld.energy = sun_s; ld.angle = math.radians(1)
        s = bpy.data.objects.new("s", ld); sc.collection.objects.link(s)
        s.rotation_euler = (math.radians(90-el), 0, 0)
    bgn.inputs["Color"].default_value = (1,1,1,1); bgn.inputs["Strength"].default_value = wstr
    sc.render.filepath = os.path.abspath("experiments/T5/_c.png"); bpy.ops.render.render(write_still=True)
    return lin_pix(sc.render.filepath)
def srgb2lin(c): return np.where(c<=0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
for lab, args in (("sun1 el25", (1, 25, 0)), ("sun1 el90", (1, 90, 0)), ("world1", (0, 25, 1.0)), ("world0.3", (0, 25, 0.3))):
    px = go(*args); print("RES", lab, "srgb", px.round(4), "lin", srgb2lin(px).round(4))
