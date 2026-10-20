# 07 GaussianShader（Phase 6 / 参照研究の適用）

実施日: 2026-10-20 / ブランチ: `claude/T7-research` / 環境: WSL2 Ubuntu、torch 2.8.0+cu128、RTX 5060 Ti（sm_120）
対象: [GaussianShader](https://github.com/Asparagus15/GaussianShader)（Inria/MPII系の非商用研究ライセンスの派生）。公式コードは `~/ext/GaussianShader` に置いて**無改変で実行**した（プロジェクトには取り込まない）。課金APIは使っていない。

## 1. 結論

- **動いた**: キャラ（Tripo メッシュを Blender で144視点描画したもの）から、法線・拡散色・鏡面色・粗さ・環境光を持つ3DGSが学習できた。テスト視点の PSNR 35.4 dB（7000反復、512px）。
- **このプロジェクトの課題への効き目は限定的**:
  - 課題の「法線の取れる3DGS」に対しては、**法線の精度はMILoのほうがずっと良い**（7章、正解メッシュとの角度誤差：MILo 中央値10° / GaussianShader 最小軸29° ほか）。
  - 「再ライティング」に対しては、**学習データの照明（太陽＋空）が拡散色と鏡面色に分離しきらず**、拡散色が黒っぽく、色の大半が鏡面側に載った（[図](img/07-gshader-layers.jpg)）。照明を変えて再ライトする用途には、照明を一様にしたデータで学習し直す必要がある（未実施）。
  - 学習が**素の3DGSの約13倍遅い**（3.7 it/s 対 49 it/s）。シェーディング関数（環境光キューブマップ・法線・反射）の計算コストによる。
- 結論として、**技法はそのまま取り込まず、考え方だけを自前実装の候補として持ち帰る**:
  1. 「拡散色＋鏡面色＋粗さ＋法線」の属性をガウシアンに持たせる（質感の分離）。
  2. 環境光（キューブマップ）と太陽を分け、拡散は法線でシェーディングする。
  3. ただし背景の焼き込み照明には使えず（二重照明になる）、キャラだけに適用する設計。

## 2. 手順（再現可能）

1. データ: `scripts/blender/render_char_dataset.py`（Blender ヘッドレス）で、キャラを T5 と同じ照明（太陽＋空グラデーション＋照り返し）で144視点描画（1024²、RGBA）。物体中心を原点に平行移動して NeRF-Synthetic 形式にする（`scripts/gaussian/make_nerf_format.py`、学習126・テスト18）。
2. 環境: `scripts/wsl/setup_gs_envs.sh`、`build_gs_ext.sh`（venv `gshader`。torch 2.8.0、**pillow 9.5.0**、open3d 0.19、nvdiffrast は MILo 同梱のものを利用）。
3. 学習: `scripts/wsl/run_gshader_char.sh char_scene_nerf -r 2 --iterations 10000`（公式READMEの `--brdf_dim 0 --sh_degree -1 --lambda_predicted_normal 2e-1 --brdf_env 512 -w --eval`）。
4. 出力の確認: 公式の `render.py`（`scripts/wsl/render_gshader_char.sh`）で diffuse / specular / roughness / normal などを書き出し。

## 3. 結果

| 項目 | 値 |
|---|---|
| 学習 | 10000反復、45分53秒（1024²→`-r 2`で512²。`-r 1` の既定だと 1.5 it/s で約5.7時間の見込みだったので縮小） |
| ガウシアン数 | 163,442（素の3DGSは244,360、MILoは72,798） |
| テスト視点 PSNR | 35.38 dB（7000反復時点、18視点）。素の3DGS（1024²）は 39.88 dB だが解像度が違うので直接比較はできない |
| PLYの属性 | 位置、法線2種（nx, nx2）、拡散色（f_dc）、不透明度、スケール、回転、粗さ、鏡面色 |

層ごとの描画（テスト視点）: gt / render / diffuse / specular / roughness / normal → [図](img/07-gshader-layers.jpg)

- normal は人体・髪・ブーツの形に沿った滑らかな色分けで、見た目の法線は妥当。
- diffuse は**暗い**（髪・服の暗色化）、specular に元の色の多くが乗っている。固定照明の1パターンだけで学習したため、「照明×アルベド」の分離が一意に決まらない（逆レンダリングの本質的な不定性）。

## 4. 失敗・つまずきと対処（公式コードは書き換えていない）

| 問題 | 原因 | 対処 |
|---|---|---|
| 拡張のビルドが `cospi/sinpi/rsqrt` の例外指定の不一致で失敗 | 新しいglibc（Ubuntu 26.04）のヘッダーと CUDA 12.8 のヘッダーの衝突 | conda 側の gcc を `nvcc -ccbin` に指定（環境変数 `NVCC_PREPEND_FLAGS`） |
| `FLT_MAX` / `uint32_t` 未定義（simple-knn、rasterizer） | 新しいCUDA/gccでは標準ヘッダーの暗黙のインクルードがない | `NVCC_PREPEND_FLAGS="-include cfloat -include cstdint"` |
| `renderutils_plugin` のリンク失敗（`-lcuda`） | WSL の libcuda は `/usr/lib/wsl/lib` | `LIBRARY_PATH` に追加 |
| `Image.fromarray(... dtype=np.byte)` で TypeError | 公式は Pillow 9.5 を前提（新しい Pillow は int8 の RGB を拒否） | venv で pillow==9.5.0 に固定 |
| `matplotlib` / `open3d` 未導入 | 公式 environment.yml（torch 1.10, Python 3.7）を使わず、新環境で導入 | pip で追加 |

## 5. 今後に持ち帰ること

- 質感の分離（拡散/鏡面/粗さ）は、**照明を一様にした学習データ**（`render_char_dataset.py --light neutral`）で再度試す価値がある。ただし得られるのは「キャラ単体の再ライト」で、背景の焼き込み照明を直すものではない。
- Unity で動かす実行時の描画（スプラットごとに法線＋環境光で陰影をつける）の設計参考になる。ただし素の3DGSの描画と違い、フラグメントごとの追加計算が要る。
- 速度が実用外（学習13倍遅）なので、公式コードを学習パイプラインに入れる選択はしない。

## 6. ファイル

| パス | 内容 |
|---|---|
| `scripts/wsl/run_gshader_char.sh`、`render_gshader_char.sh` | 学習・描画の呼び出し |
| `scripts/gaussian/make_nerf_format.py` | データセットのNeRF-Synthetic形式への変換 |
| `scripts/gaussian/eval_normals.py` | 正解メッシュとの法線比較（7章の測定） |
| `docs/img/07-gshader-layers.jpg` | 層ごとの描画 |
| Git管理外 | `experiments/T7/runs/gshader_char/`（PLY・描画一式） |

## 7. 法線の精度（正解メッシュとの比較）

Tripo のメッシュを正解にして、表面2cm以内の不透明ガウシアンについて法線の角度誤差を測った（`eval_normals.py`、結果 `experiments/T7/runs/normals_eval.json`）。

| 3DGS | 評価数 | 最小スケール軸の法線：中央値 / 30°以内 | 学習済み法線（PLY内） |
|---|---|---|---|
| 素の3DGS | 121,700 | 26.5° / 55% | なし |
| **MILo** | 70,035 | **10.1° / 84%** | なし（面の整合を学習） |
| GaussianShader | 59,382 | 29.0° / 51% | nx: 41° / nx2: 62°（座標系が不明で、結論は出せない） |

GaussianShader のPLYに保存された法線は、世界座標の面法線とは別の規約（接空間など）の可能性があり、この比較だけでは良し悪しを言えない。公式の `render.py` が出した法線画像は妥当な見た目だった。
