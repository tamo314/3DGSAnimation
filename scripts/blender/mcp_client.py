"""Blender MCPアドオンへ直接つなぐ最小クライアント(標準ライブラリのみ)。

MCPサーバー(uvx blender-mcp)を経由せず、アドオンのTCPソケットへJSONコマンドを送る。
接続確認や、Claudeセッションにblenderツールが出ていない時の代替に使う。
ポートは環境変数 BLENDER_PORT(既定9880)。9876は別プロジェクトが使うので触らない。

  python scripts/blender/mcp_client.py handshake
  python scripts/blender/mcp_client.py exec "print(bpy.app.version_string)"
  python scripts/blender/mcp_client.py exec-file path/to/script.py
"""
import json
import os
import socket
import sys

HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
PORT = int(os.environ.get("BLENDER_PORT", "9880"))


def send(cmd_type, params=None, timeout=300.0):
    with socket.create_connection((HOST, PORT), timeout=10) as s:
        s.settimeout(timeout)
        s.sendall(json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8"))
        buf = b""
        while True:
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8"))
            except ValueError:
                continue
    raise RuntimeError("接続が閉じられました: " + repr(buf[:200]))


def exec_code(code, timeout=300.0):
    return send("execute_code", {"code": code}, timeout)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "handshake"
    if mode == "handshake":
        print(json.dumps(send("get_addon_info"), ensure_ascii=False, indent=1))
    elif mode == "exec":
        print(json.dumps(exec_code(sys.argv[2]), ensure_ascii=False, indent=1))
    elif mode == "exec-file":
        with open(sys.argv[2], encoding="utf-8") as f:
            print(json.dumps(exec_code(f.read()), ensure_ascii=False, indent=1))
    else:
        sys.exit(__doc__)
