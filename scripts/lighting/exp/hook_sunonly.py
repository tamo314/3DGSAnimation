w = bpy.context.scene.world
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
bpy.data.objects["fill"].hide_render = True
