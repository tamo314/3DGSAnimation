"""T11: fal.ai で多視点画像を生成する(有料。実行前にユーザーの承認と上限額を確認済みであること)。
  python -I gen_fal.py qwen  --src IMG --az 0,45,... --el 0 --out DIR --cap 3.0 [--seed 1]
  python -I gen_fal.py banana --refs IMG1,IMG2,... --az 30,60,... --out DIR --res 2K --cap 5.0
az は本プロジェクトの規約(0=正面, +=カメラがキャラの左へ回る)。生成物は DIR/az+030.png のように保存し、meta.json に
リクエスト内容・seed・見積り費用を記録。累計の見積り費用(DIR/../ledger.json)が --cap を超えそうなら実行しない。APIキーは apikey/fal.txt から読み、出力しない。"""
import argparse, json, os, sys, time, urllib.request
import fal_client
ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["qwen", "banana"])
ap.add_argument("--src"); ap.add_argument("--refs"); ap.add_argument("--az", required=True); ap.add_argument("--el", type=float, default=0)
ap.add_argument("--out", required=True); ap.add_argument("--cap", type=float, required=True); ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--res", default="2K"); ap.add_argument("--zoom", type=float, default=5); ap.add_argument("--tag", default="")
ap.add_argument("--extra", default="")
a = ap.parse_args()
os.environ["FAL_KEY"] = open(os.path.join(os.environ.get("T11_KEYDIR", "C:/Work/3DGSAnimation/apikey"), "fal.txt")).read().strip()
os.makedirs(a.out, exist_ok=True)
ledger_path = os.path.join(os.path.dirname(os.path.abspath(a.out)), "ledger.json")
ledger = json.load(open(ledger_path)) if os.path.exists(ledger_path) else {"spent_est": 0.0, "calls": []}
UNIT = {"qwen": 0.08, "banana": 0.30 if a.res == "4K" else 0.15}   # 1枚あたりの見積り(USD)。qwenは0.035/MPで約2MPまで見込む
azs = [float(x) for x in a.az.split(",")]
est = len(azs) * UNIT[a.mode]
if ledger["spent_est"] + est > a.cap:
    sys.exit(f"cap exceeded: spent_est={ledger['spent_est']:.2f} + {est:.2f} > cap {a.cap}")
def up(p): return fal_client.upload_file(p)
def sgn(az): return az % 360
meta = []
if a.mode == "qwen":
    src = up(a.src)
    for az in azs:
        t = time.time()
        r = fal_client.subscribe("fal-ai/qwen-image-edit-2511-multiple-angles", arguments={
            "image_urls": [src], "horizontal_angle": (-az) % 360, "vertical_angle": a.el, "zoom": a.zoom, "seed": a.seed, "num_images": 1,
            "output_format": "png", "enable_safety_checker": False, "additional_prompt": a.extra or None})
        url = r["images"][0]["url"]; fn = os.path.join(a.out, f"az{az:+04.0f}_el{a.el:+03.0f}{a.tag}.png")
        urllib.request.urlretrieve(url, fn); meta.append({"az": az, "el": a.el, "file": fn, "seed": r.get("seed"), "prompt": r.get("prompt"), "sec": time.time() - t})
        print("ok", fn, flush=True)
else:
    refs = [up(p) for p in a.refs.split(",")]
    for az in azs:
        side = "left" if (az % 360) < 180 else "right"
        prompt = (f"Same character as in the reference images (reference images show the front, side, three-quarter and back views of one character; keep the costume, hair, face, accessories and proportions exactly the same). "
                  f"Render a full-body image of this character with the camera orbited horizontally {abs(((az + 180) % 360) - 180):.0f} degrees from the front view toward the character's {side} side "
                  f"({'front view' if az % 360 == 0 else 'back view' if az % 360 == 180 else 'seen from the character' + chr(39) + 's ' + side}), at eye level, long-focal-length camera so the perspective is nearly flat, "
                  f"the character standing in the same pose, same size and centered, plain flat light gray background, soft even studio lighting, high detail anime style. {a.extra}")
        t = time.time()
        r = fal_client.subscribe("fal-ai/nano-banana-pro/edit", arguments={
            "prompt": prompt, "image_urls": refs, "aspect_ratio": "4:5", "resolution": a.res, "output_format": "png", "seed": a.seed, "num_images": 1, "limit_generations": True})
        url = r["images"][0]["url"]; fn = os.path.join(a.out, f"az{az:+04.0f}{a.tag}.png")
        urllib.request.urlretrieve(url, fn); meta.append({"az": az, "file": fn, "prompt": prompt, "sec": time.time() - t})
        print("ok", fn, flush=True)
ledger["spent_est"] += est; ledger["calls"].append({"mode": a.mode, "n": len(azs), "est": est, "tag": a.tag})
json.dump(ledger, open(ledger_path, "w"), indent=1)
mp = os.path.join(a.out, "meta.json"); old = json.load(open(mp)) if os.path.exists(mp) else []
json.dump(old + meta, open(mp, "w"), indent=1, ensure_ascii=False)
