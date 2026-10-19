"""参照画像 forest1（補助: forest2-5）から太陽方向・色温度・環境光を推定し、
assets/generated/background/lighting_estimate.json を出力する。

依存: numpy, Pillow のみ（クラウドで完結。課金APIなし）。
使い方: python scripts/analysis/estimate_lighting.py <参照画像フォルダ> [出力JSON]
測定ボックスはすべて forest1.png（1448x1086）のピクセル座標。
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from estimate_colors import lin_to_srgb8, srgb_to_lin, xy_cct  # noqa: E402
from estimate_edges import run as edge_widths  # noqa: E402
from estimate_shafts import shaft_angle  # noqa: E402

W, H = 1448, 1086
LUM = np.array([0.2126, 0.7152, 0.0722])

# --- 測定点（forest1 のピクセル座標 x0,y0,x1,y1） ---
SHAFT_BOX = (950, 40, 1300, 420)           # 右上の光芒
SOIL_BOX = (780, 790, 1010, 1080)          # 手前の小道（土）
SKY_BOX = (880, 0, 1130, 190)              # 樹冠の隙間の青空
STONE_PAIRS = {                            # 無彩色に近い石の (日向, 日陰)
    "stone_step_1": ((880, 697, 955, 704), (905, 713, 955, 726)),
    "stone_step_2": ((960, 699, 1010, 706), (960, 713, 1010, 726)),
}
PILLAR_SHADE = (1230, 600, 1290, 630)      # 右の石柱の正面（逆光で日陰）
PILLAR_SHADE2 = (1225, 690, 1260, 740)     # 同 下部
PILLAR_TOP = (1190, 572, 1330, 590)        # 同 上面（日向）
GRASS_LIT = (837, 788, 897, 803)           # 日向の草（下方向の反射光の色）

# --- 視線方向の仮定 ---
SUN_VP = {"x": (1280, 1450), "y": (-120, 20)}   # 光芒の収束点=太陽の画像上の位置（画面外右上）
HFOV_DEG = (60, 80)                              # AI画像の水平画角の仮定
PITCH_DOWN_DEG = (0, 4)                          # カメラの俯角の仮定
PATH_VP_X = (940, 1010)                          # 小道/アーチの方向（画像上の x）


def mean_lin(img, box):
    x0, y0, x1, y1 = box
    return srgb_to_lin(img[y0:y1, x0:x1].reshape(-1, 3)).mean(axis=0)


def daylight_xy(cct):
    t = float(cct)
    x = -4.6070e9 / t**3 + 2.9678e6 / t**2 + 0.09911e3 / t + 0.244063
    y = -3.0 * x * x + 2.87 * x - 0.275
    return x, y


def xy_to_lin_rgb(x, y):
    X, Z = x / y, (1 - x - y) / y
    rgb = np.linalg.inv(np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])) @ np.array([X, 1.0, Z])
    return np.clip(rgb / rgb.max(), 0, 1)


def hex8(lin):
    return "#%02x%02x%02x" % tuple(lin_to_srgb8(lin))


def sun_direction_samples(n=20000, seed=1):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        u = rng.uniform(*SUN_VP["x"]); v = rng.uniform(*SUN_VP["y"])
        f = (W / 2) / math.tan(math.radians(rng.uniform(*HFOV_DEG) / 2))
        p = math.radians(rng.uniform(*PITCH_DOWN_DEG))
        dx, dy = (u - W / 2) / f, (v - H / 2) / f          # カメラ座標: x右, y下, z前
        n_ = math.sqrt(dx * dx + dy * dy + 1)
        sin_el = (-dy * math.cos(p) - math.sin(p)) / n_    # 俯角 p のカメラでの水平面からの仰角
        el = math.degrees(math.asin(sin_el))
        az_cam = math.degrees(math.atan2(dx, math.cos(p) - dy * math.sin(p)))  # 光軸の水平投影からの方位
        bearing = math.degrees(math.atan2((rng.uniform(*PATH_VP_X) - W / 2) / f, math.cos(p)))
        out.append((az_cam, el, bearing))
    return np.array(out)


def blender_euler_deg(az_from_plus_y_to_plus_x, el):
    """Blender の太陽ライト(-Z方向に照らす)で、太陽が +Y 側・+X 側にある向きを作る XYZ オイラー角。"""
    az, e = math.radians(az_from_plus_y_to_plus_x), math.radians(el)
    rx, rz = math.pi / 2 - e, math.pi - az
    # 検算: -Z を回した結果が「太陽から地面へ向かう向き」と一致するか
    cx, sx, cz, sz = math.cos(rx), math.sin(rx), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    d = Rz @ Rx @ np.array([0, 0, -1.0])
    want = -np.array([math.sin(az) * math.cos(e), math.cos(az) * math.cos(e), math.sin(e)])
    assert np.allclose(d, want, atol=1e-9), (d, want)
    return [round(math.degrees(rx), 1), 0.0, round(math.degrees(rz), 1)]


def main(ref_dir, out_path):
    p1 = os.path.join(ref_dir, "forest1.png")
    img = np.asarray(Image.open(p1).convert("RGB"))
    assert img.shape[:2] == (H, W), img.shape

    # 1) 光芒の向き（画像上）
    shafts = {}
    for i in range(1, 6):
        a, c = shaft_angle(os.path.join(ref_dir, f"forest{i}.png"), SHAFT_BOX)
        shafts[f"forest{i}"] = {"angle_from_vertical_deg": round(float(a), 1), "coherence": round(float(c), 2)}
    # 2) 太陽方向（モンテカルロで不確かさを出す）
    s = sun_direction_samples()
    az_cam = np.percentile(s[:, 0], [10, 50, 90]); el = np.percentile(s[:, 1], [10, 50, 90])
    bearing = np.percentile(s[:, 2], [10, 50, 90])
    az_world = s[:, 0] - s[:, 2]                                   # +Y(小道/アーチ方向)基準
    azw = np.percentile(az_world, [10, 50, 90])
    az_w, el_m = float(azw[1]), float(el[1])
    d_to_sun = [math.sin(math.radians(az_w)) * math.cos(math.radians(el_m)),
                math.cos(math.radians(az_w)) * math.cos(math.radians(el_m)),
                math.sin(math.radians(el_m))]
    # 3) 色: 無彩色に近い石の (日向-日陰) = 直射光の色、日陰 = 環境光の色
    sun_ccts, sun_vecs, shade_vecs, ratios = [], [], [], []
    for name, (lit_b, shade_b) in STONE_PAIRS.items():
        lit, shade = mean_lin(img, lit_b), mean_lin(img, shade_b)
        d = np.clip(lit - shade, 1e-6, None)
        sun_ccts.append(xy_cct(d)[2]); sun_vecs.append(d / d.max()); shade_vecs.append(shade / shade.max())
        ratios.append((d @ LUM) / (shade @ LUM))
    pillar_shade = (mean_lin(img, PILLAR_SHADE) + mean_lin(img, PILLAR_SHADE2)) / 2; pillar_top = mean_lin(img, PILLAR_TOP)
    ratios.append(float((pillar_top - pillar_shade) @ LUM / (pillar_shade @ LUM)))
    sun_cct = float(np.median(sun_ccts))
    # 土（路面）: 日向/日陰の分離
    from estimate_colors import otsu, soil_mask
    x0, y0, x1, y1 = SOIL_BOX
    px = img[y0:y1, x0:x1].reshape(-1, 3); px = px[soil_mask(px)]
    lum = srgb_to_lin(px) @ LUM; t = otsu(lum)
    lit_frac = float((lum > t).mean())
    soil_lit = srgb_to_lin(px[lum > t]).mean(axis=0); soil_shade = srgb_to_lin(px[lum <= t]).mean(axis=0)
    soil_ratio = float(((soil_lit - soil_shade) @ LUM) / (soil_shade @ LUM))
    ratios.append(soil_ratio)
    # 水平面どうしの比較ができる 土(4.8) と 石段1(3.8) の平均を採用。他は反射率/向きが混ざるため範囲の根拠にとどめる
    sun_to_amb = float((soil_ratio + ratios[0]) / 2)
    # 日向の連続長（小道の斑の大きさ）: 土マスク上の水平ランレングス(px)
    sm = soil_mask(img[y0:y1, x0:x1].reshape(-1, 3)).reshape(y1 - y0, x1 - x0)
    L = (srgb_to_lin(img[y0:y1, x0:x1].reshape(-1, 3)) @ LUM).reshape(y1 - y0, x1 - x0) > t
    runs = []
    for row, srow in zip(L, sm):
        cur = 0
        for v, ok in zip(row, srow):
            if v and ok: cur += 1
            elif cur: runs.append(cur); cur = 0
        if cur: runs.append(cur)
    runs = np.array([r for r in runs if r >= 3])
    srt = np.sort(runs); cs = np.cumsum(srt); wmed = float(srt[np.searchsorted(cs, cs[-1] / 2)]) if len(srt) else 0.0
    # スケール: 小道の幅 約1.5m が y=900 付近で約 220px → 約 6.8 mm/px（小道幅1.2〜1.8mの仮定）
    mm_per_px = 1500 / 220
    edges = edge_widths(p1, SOIL_BOX); edge_med = float(np.median(edges)) if len(edges) else float("nan")
    spx = img[SKY_BOX[1]:SKY_BOX[3], SKY_BOX[0]:SKY_BOX[2]].reshape(-1, 3).astype(int)
    spx = spx[(spx[:, 2] > spx[:, 0] + 25) & (spx[:, 2] > spx[:, 1] + 5) & (spx[:, 2] > 150)]
    sky_lin = srgb_to_lin(spx).mean(axis=0)
    ground = (mean_lin(img, GRASS_LIT) + soil_lit) / 2

    eff = pillar_shade / pillar_shade.max()
    up_c = 0.65 * eff + 0.35 * (sky_lin / sky_lin.max())      # 上向き: 空の青を一部混ぜる（初期値）
    low_c = 0.5 * eff + 0.5 * (ground / ground.max())         # 下向き: 地面の反射光を一部混ぜる（初期値）
    sx, sy = daylight_xy(sun_cct)
    sun_rgb = xy_to_lin_rgb(sx, sy)
    el_r = math.radians(el_m)
    shadow_len = 1 / math.tan(el_r)
    out = {
        "schema_version": 1,
        "primary_image": "assets/reference/background/forest1.png",
        "method": "scripts/analysis/estimate_lighting.py（画像のみから推定。クラウド完結・課金APIなし）",
        "coordinate_frame": "ワールド座標=統合シーンの契約(Z上・右手系・m)。+Y=小道中央のキャラ設置点から石造アーチへ向かう方向、+X=カメラ(-Y側)から見て右。方位は +Y から +X へ測る(上から見て時計回り)。仰角は水平面から。",
        "sun": {
            "azimuth_deg": round(az_w, 1),
            "azimuth_deg_range": [round(az_w - 9, 1), round(az_w + 9, 1)],
            "azimuth_deg_montecarlo_p10_p90": [round(float(azw[0]), 1), round(float(azw[2]), 1)],
            "elevation_deg": round(el_m, 1),
            "elevation_deg_range": [round(el_m - 7, 1), round(el_m + 7, 1)],
            "elevation_deg_montecarlo_p10_p90": [round(float(el[0]), 1), round(float(el[2]), 1)],
            "range_note": "range は目視の読み取り誤差・画角の仮定を含めた保守的な幅。montecarlo は仮定の範囲だけを振った幅（狭く出る）。",
            "direction_to_sun_world": [round(v, 3) for v in d_to_sun],
            "light_travel_direction_world": [round(-v, 3) for v in d_to_sun],
            "blender_sun_rotation_euler_deg_XYZ": blender_euler_deg(az_w, el_m),
            "position_relative_to_view": "背後〜右上奥の逆光（半逆光）。カメラの正面(-Y側)を向く面は日陰になる。",
            "color_temperature_K": int(round(sun_cct / 50) * 50),
            "color_temperature_K_range": [4800, 5800],
            "color_linear_rgb": [round(float(v), 3) for v in sun_rgb],
            "color_srgb_hex": hex8(sun_rgb),
            "angular_diameter_deg_recommended": 6.0,
            "angular_diameter_deg_range": [3.0, 15.0],
        },
        "ambient": {
            "sun_to_ambient_irradiance_ratio_on_horizontal": round(sun_to_amb, 1),
            "sun_to_ambient_ratio_range": [3.0, 6.0],
            "effective_shade_color": {"color_linear_rgb": [round(float(v), 3) for v in eff],
                                      "cct_K_as_rendered": int(round(xy_cct(pillar_shade)[2] / 100) * 100),
                                      "note": "無彩色に近い石の日陰面が実際に示す色。日陰の見た目の根拠。青空よりずっと中立〜暖色（樹冠と地面の反射光が効く）。"},
            "world_upper_color_linear_rgb_initial": [round(float(v), 3) for v in up_c / up_c.max()],
            "world_lower_color_linear_rgb_initial": [round(float(v), 3) for v in low_c / low_c.max()],
            "upper_sky": {"color_srgb_hex": hex8(sky_lin), "color_linear_rgb": [round(float(v), 3) for v in sky_lin / sky_lin.max()],
                          "cct_K_as_rendered": int(round(xy_cct(sky_lin)[2] / 100) * 100)},
            "lower_ground_bounce": {"color_srgb_hex": hex8(ground), "color_linear_rgb": [round(float(v), 3) for v in ground / ground.max()],
                                    "relative_intensity_vs_upper": 0.5},
            "shade_on_neutral_stone": {"color_srgb_hex": hex8(pillar_shade), "cct_K_as_rendered": int(round(xy_cct(pillar_shade)[2] / 100) * 100)},
            "blender_hint": ("太陽の強さ S と World の背景の強さ A は S*sin(仰角)/(pi*A) = 比 を満たすように選ぶ（例: S=3.0 なら A≈{:.2f}）。絶対値ではなく比が根拠。").format(3.0 * math.sin(math.radians(el_m)) / (math.pi * sun_to_amb)),
        },
        "shadow": {
            "cast_direction_horizontal_world": [round(-d_to_sun[0] / math.cos(el_r), 3), round(-d_to_sun[1] / math.cos(el_r), 3)],
            "length_per_unit_height": round(shadow_len, 2),
            "length_for_1p2m_character_m": round(1.2 * shadow_len, 2),
            "falls_toward": "カメラ側(-Y)かつ左(-X)。接地影はキャラの手前左へ伸びる。",
            "path_shadow_edge_width_10_90_px": round(edge_med, 1),
            "path_shadow_edge_width_mm_approx": round(edge_med * mm_per_px),
            "softness_note": "縁(10-90%)は約7cm。遮蔽物の高さ0.2〜1mなら太陽の見かけの直径に換算して約4〜19度。AI生成画像の縁は物理的に正確でないため、太陽の直径は6度を初期値にして Phase 4-B で背景の影と見比べて調整する。",
        },
        "dappled_light": {
            "sunlit_fraction_on_path": round(lit_frac, 2),
            "length_weighted_median_sunlit_run_px": wmed,
            "length_weighted_median_sunlit_run_m_approx": round(wmed * mm_per_px / 1000, 2),
            "note": "小道の約2割が日向。日向の水平方向の連続長（長さ加重の中央値）が斑の幅の目安。キャラの木漏れ日ゴボは日向率20〜30%を目安に。",
        },
        "shafts_image": {
            "slant_from_vertical_deg": -32,
            "note": "右上→左下へ傾く光芒。光芒の収束点（=太陽の画像上の位置）は画面右上の外側。",
            "sun_image_position_px_assumed": [1370, -50],
            "per_image_structure_tensor": shafts,
            "per_image_caveat": "構造テンソルは葉の高周波が混ざり coherence が低く参考値。forest1 は目視の線引き(-32〜-35度)と一致。",
        },
        "geometry_assumptions": {
            "horizontal_fov_deg": list(HFOV_DEG), "camera_pitch_down_deg": list(PITCH_DOWN_DEG),
            "camera_axis_to_path_bearing_deg_p10_p90": [round(float(bearing[0]), 1), round(float(bearing[2]), 1)],
            "sun_azimuth_relative_to_camera_axis_deg_median": round(float(az_cam[1]), 1),
            "camera_axis_to_path_bearing_deg_median": round(float(bearing[1]), 1),
            "sun_azimuth_relative_to_camera_axis_deg_p10_p90": [round(float(az_cam[0]), 1), round(float(az_cam[2]), 1)],
            "mm_per_px_on_path": round(mm_per_px, 1),
        },
        "uncertainty_summary": "方位 ±9度、仰角 ±7度程度（画角・俯角・光芒の収束点の仮定による）。色温度 ±500K（画像の色調補正と石の反射率を中立と仮定）。Phase 4-B で背景に焼き込まれた影の向きを測って補正すること。",
        "recommended_for_phase_4b": {
            "sun_euler_deg_XYZ": blender_euler_deg(az_w, el_m),
            "sun_color_linear_rgb": [round(float(v), 3) for v in sun_rgb],
            "sun_angle_deg": 6.0,
            "world_upper_color_linear_rgb": [round(float(v), 3) for v in up_c / up_c.max()],
            "world_lower_color_linear_rgb": [round(float(v), 3) for v in low_c / low_c.max()],
            "character_front_is_in_shade": True,
            "expect": "キャラの正面(カメラ向き)は日陰になり、頭頂・肩・髪の右上縁にだけ直射と縁取り光が乗る。接地影は手前左へ約2倍の身長分伸びる。",
        },
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("sun", "ambient", "shadow", "dappled_light")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ref = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "assets/generated/background/lighting_estimate.json"
    main(ref, out)
