import os
out = os.path.abspath("experiments/T5/out_shadow")
def run(tag, **kw):
    for k, v in kw.items():
        setattr(sp, k, v)
    sp.r2_shadows = True
    sp.r2_shadow_light = sun
    try:
        print("T5 refresh", bpy.ops.sna.dgs_render_refresh_shadows_16f2b())
    except Exception as e:
        print("T5 refresh failed", e)
    print("T5 render", tag, bi.render_all(out, names=["character_medium"], tag=tag))
sp.r2_relight = True
run("s_str0p01_", r2_relight_strength=0.01)
run("s_str0p1_", r2_relight_strength=0.1)
run("s_str0p3_", r2_relight_strength=0.3)
