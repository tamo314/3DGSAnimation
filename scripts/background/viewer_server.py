#!/usr/bin/env python3
"""確認用ビューアの簡易サーバ(独自実装)。

  /            -> tools/viewer/ の静的ファイル
  /gen/...     -> assets/generated/background/(メインのフォルダ側。SPZ等の大きなバイナリ置き場)
  POST /save?name=X.png -> 画面キャプチャを captures/ に保存

使い方: python viewer_server.py [--port 8765] [--captures DIR]
"""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parents[2]
GEN = Path("C:/Work/3DGSAnimation/assets/generated/background")


def make_handler(captures: Path):
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(REPO / "tools" / "viewer"), **k)

        def translate_path(self, path):
            p = urlparse(path).path
            if p.startswith("/gen/"):
                return str(GEN / p[len("/gen/"):])
            return super().translate_path(path)

        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_POST(self):
            u = urlparse(self.path)
            if u.path != "/save":
                self.send_error(404)
                return
            name = Path(parse_qs(u.query).get("name", ["cap.png"])[0]).name
            data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            captures.mkdir(parents=True, exist_ok=True)
            (captures / name).write_bytes(data)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"saved {name} ({len(data)} bytes)".encode())

        def log_message(self, *a):
            pass

    return H


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--captures", default=str(GEN / "captures"))
    a = ap.parse_args()
    print(f"serving on http://127.0.0.1:{a.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Path(a.captures))).serve_forever()
