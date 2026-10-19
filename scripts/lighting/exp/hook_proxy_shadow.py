import os
out = os.path.abspath("experiments/T5/out_proxy")
sp.r2_relight = False
sp.r2_shadow_proxy = True
for lim, cut, tag in ((300000, 0.5, "p300k_c0p5_"),):
    sp.r2_shadow_proxy_limit = lim
    sp.r2_shadow_proxy_cutoff = cut
    print("T5 build", bpy.ops.sna.dgs_render_build_shadow_proxies_5b787())
    print("T5 cards", len(bpy.data.objects), [o.name for o in bpy.data.objects if o.type != "CAMERA"][:10])
    print("T5 render", tag, bi.render_all(out, names=["character_medium", "front_wide"], tag=tag))
