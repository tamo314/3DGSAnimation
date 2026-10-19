"""統合シーンの検証用プローブ(T4): 真上カメラ、深度から地面高さ、小道中心の確認。
Blender内で: import probe_integration as pr; pr.top_view(out, height=6.0, ...)
"""
from __future__ import annotations

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spike_common as sc  # noqa: E402


def _cam(name, pos, target, focal=24.0, ortho_scale=None):
    c = sc.make_camera(name, pos, target, focal)
    if ortho_scale and False:  # KIRIは平行投影非対応(崩れる)ので使わない
        c.data.type = "ORTHO"
        c.data.ortho_scale = ortho_scale
    return c


def top_view(out_dir, tag="top", center=(0.0, 0.0), height=6.0, ortho=8.0, hide_char=False, depth=False):
    """真下向きの正射影で center 付近を撮る。KIRIの深度(_depth)も欲しいときは depth=True。"""
    os.makedirs(out_dir, exist_ok=True)
    cam = _cam(f"probe_{tag}", (center[0], center[1], height), (center[0], center[1], 0.0), ortho_scale=ortho)
    cam.rotation_euler = (0.0, 0.0, 0.0)  # 真下(-Z)、画面上=+Y
    bpy.context.scene.camera = cam
    ch = bpy.data.objects.get("character")
    if hide_char and ch:
        for o in [ch] + list(ch.children):
            o.hide_render = True
    r = sc.kiri_render(os.path.join(os.path.abspath(out_dir), f"{tag}_"), comp=True, sh_degree=0, depth=depth)
    if hide_char and ch:
        for o in [ch] + list(ch.children):
            o.hide_render = False
    bpy.data.objects.remove(cam)
    return r
