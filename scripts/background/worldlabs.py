#!/usr/bin/env python3
"""World Labs Marble API の最小クライアント(独自実装、標準ライブラリのみ)。

キーは環境変数 WLT_API_KEY から読む。無ければ apikey/worldlab.txt を探す(値は出力しない)。
課金が発生するのは `generate` のみ。生成回数の上限ガードを持つ。

使い方:
  python worldlabs.py credits
  python worldlabs.py generate --image IN.png --model marble-1.0-draft --exp T1-d1 --label "..."
  python worldlabs.py download --world-json experiments/T1-d1/world.json --out-dir DIR
  python worldlabs.py export-ply --world-id ID --resolution full_res --out OUT.ply
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.worldlabs.ai/marble/v1"
REPO = Path(__file__).resolve().parents[2]
EXPERIMENTS = REPO / "experiments"
# 世界生成の総回数の上限(ユーザー方針: 最大5回)。既定では4回目までで止め、5回目は --approved-last で明示する。
HARD_LIMIT = 5
SOFT_LIMIT = 4


def load_key() -> str:
    key = os.environ.get("WLT_API_KEY") or os.environ.get("WORLD_LABS_API_KEY")
    if key:
        return key.strip()
    for base in (REPO, REPO.parent / "3DGSAnimation"):
        f = base / "apikey" / "worldlab.txt"
        if f.exists():
            return f.read_text(encoding="utf-8").strip()
    sys.exit("World Labs APIキーが見つかりません(WLT_API_KEY 未設定)")


def call(method, path, body=None, timeout=120):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"WLT-Api-Key": load_key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        sys.exit(f"HTTP {e.code} {path}: {detail}")


def credits():
    return float(call("GET", "/credits").get("remaining_credits", -1))


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return dest


def count_generations():
    n = 0
    for p in EXPERIMENTS.glob("*/meta.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("kind") == "world_generation":
                n += 1
        except Exception:
            pass
    return n


def save_meta(exp, meta):
    (exp / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_generate(a):
    used = count_generations()
    limit = HARD_LIMIT if a.approved_last else SOFT_LIMIT
    if used >= limit:
        sys.exit(f"生成回数 {used} 回が上限 {limit} に達しています。ユーザー確認が必要です。")
    exp = EXPERIMENTS / a.exp
    if (exp / "meta.json").exists():
        sys.exit(f"{exp} は既に存在します")

    img = Path(a.image)
    prompt = {
        "type": "image",
        "image_prompt": {
            "source": "data_base64",
            "data_base64": base64.b64encode(img.read_bytes()).decode(),
            "extension": img.suffix.lstrip(".").lower(),
        },
        "is_pano": False,
    }
    if a.text_prompt:
        prompt["text_prompt"] = a.text_prompt
        prompt["disable_recaption"] = bool(a.disable_recaption)
    req = {"display_name": a.exp[:64], "model": a.model, "world_prompt": prompt}
    if a.seed is not None:
        req["seed"] = a.seed

    before = credits()
    meta = {
        "kind": "world_generation", "provider": "world-labs", "model": a.model,
        "label": a.label, "input_image": str(img), "text_prompt": a.text_prompt,
        "disable_recaption": bool(a.disable_recaption), "seed": a.seed,
        "submitted_at": datetime.now(timezone.utc).isoformat(), "credits_before": before,
    }

    op = call("POST", "/worlds:generate", req)  # 失敗時は何も記録しない(回数に数えない)
    op_id = op.get("operation_id") or op.get("id")
    meta["operation_id"] = op_id
    exp.mkdir(parents=True, exist_ok=True)
    save_meta(exp, meta)
    print(f"submitted operation {op_id}; polling...", flush=True)
    while not op.get("done"):
        time.sleep(15)
        op = call("GET", f"/operations/{op_id}")
    meta["completed_at"] = datetime.now(timezone.utc).isoformat()
    meta["credits_after"] = credits()
    meta["credits_spent"] = before - meta["credits_after"]
    meta["cost"] = op.get("cost")
    if op.get("error"):
        meta["error"] = op["error"]
        save_meta(exp, meta)
        sys.exit(f"失敗: {op['error']}")
    world = op["response"]
    (exp / "world.json").write_text(json.dumps(world, indent=2, ensure_ascii=False), encoding="utf-8")
    meta["world_id"] = world.get("world_id") or world.get("id")
    meta["world_marble_url"] = world.get("world_marble_url")
    save_meta(exp, meta)
    print(json.dumps({"world_id": meta["world_id"], "credits_spent": meta["credits_spent"]}, ensure_ascii=False))


def cmd_download(a):
    world = json.loads(Path(a.world_json).read_text(encoding="utf-8"))
    assets = world.get("assets", {})
    out = Path(a.out_dir)
    got = []
    for k, u in (assets.get("splats", {}).get("spz_urls") or {}).items():
        if u and (not a.only or k in a.only.split(",")):
            got.append(str(download(u, out / f"{a.prefix}{k}.spz")))
    if not a.splats_only:
        u = assets.get("mesh", {}).get("collider_mesh_url")
        if u:
            got.append(str(download(u, out / f"{a.prefix}collider.glb")))
        u = assets.get("imagery", {}).get("pano_url")
        if u:
            got.append(str(download(u, out / f"{a.prefix}pano.png")))
        u = assets.get("thumbnail_url")
        if u:
            got.append(str(download(u, out / f"{a.prefix}thumbnail.webp")))
    print("\n".join(got))


def cmd_export_ply(a):
    op = call("POST", f"/worlds/{a.world_id}:export",
              {"asset_type": "splats", "format": "ply", "resolution": a.resolution})
    op_id = op.get("operation_id")
    while not op.get("done"):
        time.sleep(5)
        op = call("GET", f"/operations/{op_id}")
    if op.get("error"):
        sys.exit(f"export失敗: {op['error']}")
    print(download(op["response"]["url"], Path(a.out)))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("credits")
    g = sub.add_parser("generate")
    g.add_argument("--image", required=True)
    g.add_argument("--model", default="marble-1.1")
    g.add_argument("--exp", required=True, help="experiments/<exp>/ に記録")
    g.add_argument("--label", default="")
    g.add_argument("--text-prompt")
    g.add_argument("--disable-recaption", action="store_true")
    g.add_argument("--seed", type=int)
    g.add_argument("--approved-last", action="store_true", help="ユーザー承認済みの5回目を許可")
    d = sub.add_parser("download")
    d.add_argument("--world-json", required=True)
    d.add_argument("--out-dir", required=True)
    d.add_argument("--prefix", default="")
    d.add_argument("--only", help="例: full_res,500k")
    d.add_argument("--splats-only", action="store_true")
    e = sub.add_parser("export-ply")
    e.add_argument("--world-id", required=True)
    e.add_argument("--resolution", default="full_res")
    e.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "credits":
        print(credits())
    else:
        {"generate": cmd_generate, "download": cmd_download, "export-ply": cmd_export_ply}[a.cmd](a)


if __name__ == "__main__":
    main()
