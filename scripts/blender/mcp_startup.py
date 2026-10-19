"""Blender起動時スクリプト: このリポジトリ専用のBlender MCPサーバーをポート9877で起動する。

別プロジェクト(CatAnime)のBlenderが既定ポート9876を使うため、衝突を避けて9877を使う。
`blender --factory-startup --python scripts/blender/mcp_startup.py` で起動する
(launch_blender_mcp.ps1 経由が簡単)。.mcp.json の BLENDER_PORT と一致させること。

アドオンのregister()は scene.blendermcp_port(既定9876)でサーバーを自動起動する。
Windowsでは SO_REUSEADDR により使用中の9876にもbindできてしまい、他のBlenderの接続を
横取りしかねないので、アドオンを有効化する前に 9876 へのbindを PORT へ読み替える。
"""
import os
import socket

import bpy

PORT = int(os.environ.get("GS_BLENDER_MCP_PORT", "9877"))
_orig_bind = socket.socket.bind


def _bind(self, address):
    if isinstance(address, tuple) and len(address) >= 2 and address[1] == 9876:
        address = (address[0], PORT) + tuple(address[2:])
    return _orig_bind(self, address)


socket.socket.bind = _bind
bpy.ops.preferences.addon_enable(module="blender_mcp")

server = getattr(bpy.types, "blendermcp_server", None)
print(f"[mcp_startup] running={getattr(server, 'running', None)} (bind port -> {PORT})")

# KIRI Engine 3DGS Render(拡張機能)。launch_blender_mcp.ps1 が BLENDER_USER_EXTENSIONS で
# このプロジェクト専用の拡張フォルダを指す(ユーザー共通の設定は変更しない)。
KIRI = "bl_ext.user_default.dgs_render_by_kiri_engine"
if os.environ.get("BLENDER_USER_EXTENSIONS"):
    try:
        bpy.ops.preferences.addon_enable(module=KIRI)
        print("[mcp_startup] KIRI enabled:", KIRI in bpy.context.preferences.addons)
    except Exception as e:  # 未導入でもMCPは使えるようにする
        print("[mcp_startup] KIRI enable failed:", e)
