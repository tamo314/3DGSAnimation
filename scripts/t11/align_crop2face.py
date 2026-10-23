"""T11: 部位アップ(寄り画像)の倍率・位置を、元になった顔アップ(カメラ既知)に対する2D位置合わせ(拡大率+平行移動のテンプレートマッチ)で決める。
粗い3DGSに頼らないので、肌が滑らかな口まわりでも決まる。寄り画像は顔アップから生成しているので、同じ絵が拡大されているだけ。
  python align_crop2face.py --crops CROPS_JSON(file=RGBAでなく元のPNG, az, name) --faces FACE_VIEWS_JSON(名目方位ごとの顔アップのカメラ: zoom,tz,sx,az,file(元PNG)) --out OUT_JSON
方位が10°の倍数でない寄り画像は、両隣の顔アップそれぞれに合わせた結果を平均する。出力: crops_jsonにzoom,tz,sx,syを足したもの。"""
import argparse, json, math
import numpy as np, cv2
ap = argparse.ArgumentParser(); ap.add_argument("--crops", required=True); ap.add_argument("--faces", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--smin", type=float, default=1.6); ap.add_argument("--smax", type=float, default=3.4); ap.add_argument("--blur", type=float, default=1.5); ap.add_argument("--W", type=int, default=1024); ap.add_argument("--H", type=int, default=1280); ap.add_argument("--fig", type=float, default=0.875)
a = ap.parse_args()
def gray(f, scale=0.5):
    im = cv2.imread(f, cv2.IMREAD_COLOR); im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255; return cv2.GaussianBlur(g, (0, 0), a.blur)
faces = {int(round(v["az"])): v for v in json.load(open(a.faces)) if v["name"].startswith("c10_az")}
out = []
for c in json.load(open(a.crops)):
    az = int(c["az"]); lo = int(math.floor(az / 10) * 10); hi = lo + 10; cand = [x for x in ([lo] if lo == az else [lo, hi]) if x in faces]
    gc0 = gray(c["file"]); ests = []
    for fa in cand:
        fv = faces[fa]; gf = gray(fv["file"]); H, W = gf.shape; best = None
        for s in np.arange(a.smin, a.smax + 1e-6, 0.04):
            th, tw = int(round(H / s)), int(round(W / s)); t = cv2.resize(gc0, (tw, th), interpolation=cv2.INTER_AREA)
            r = cv2.matchTemplate(gf, t, cv2.TM_CCOEFF_NORMED); _, mx, _, loc = cv2.minMaxLoc(r)
            if best is None or mx > best[0]: best = (mx, s, loc, tw, th)
        mx, s, loc, tw, th = best
        # 精密化: 倍率を細かく
        for s2 in np.arange(s - 0.04, s + 0.0401, 0.01):
            th2, tw2 = int(round(H / s2)), int(round(W / s2)); t = cv2.resize(gc0, (tw2, th2), interpolation=cv2.INTER_AREA)
            r = cv2.matchTemplate(gf, t, cv2.TM_CCOEFF_NORMED); _, m2, _, l2 = cv2.minMaxLoc(r)
            if m2 > mx: mx, s, loc, tw, th = m2, s2, l2, tw2, th2
        cx, cy = loc[0] + tw / 2, loc[1] + th / 2; dx, dy = (cx - W / 2) / W * a.W, (cy - H / 2) / H * a.H        # キャンバス(1024x1280)上の、顔アップ中心からの寄り画像中心の位置(px)
        ppu = a.H * a.fig * fv["zoom"] / 2.0                                                                     # 顔アップのカメラで、注視面の1ワールド単位が何pxか
        ests.append({"ncc": mx, "s": s, "zoom": fv["zoom"] * s, "tz": fv["tz"] - dy / ppu, "sx": fv["sx"] + dx / ppu, "az_face": fa})
    r = dict(c); r["zoom"] = float(np.mean([e["zoom"] for e in ests])); r["tz"] = float(np.mean([e["tz"] for e in ests])); r["sx"] = float(np.mean([e["sx"] for e in ests])); r["sy"] = 0.0
    r["ncc"] = [e["ncc"] for e in ests]; r["az"] = c["az"]; out.append(r)
    print(c["name"], "zoom %.2f tz %.3f sx %.3f" % (r["zoom"], r["tz"], r["sx"]), "ncc", [round(n, 2) for n in r["ncc"]], flush=True)
json.dump(out, open(a.out, "w"), indent=1)
