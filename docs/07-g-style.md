# 07 G-Style（Phase 6 / 参照研究の適用）

実施日: 2026-10-20 / ブランチ: `claude/T7-research` / 環境: WSL2 Ubuntu、torch 2.8.0+cu128、RTX 5060 Ti（sm_120）
対象: [G-Style](https://github.com/AronKovacs/g-style)（Inria/MPII系の非商用研究ライセンス）。公式コードは `~/ext/g-style` に置いて**無改変で実行**した（プロジェクトには取り込まない）。課金APIは使っていない。

## 1. 結論

- **動いたが、キャラの質感改善には使えない。** スタイル画像（森のコンセプトアート `forest1.png`）を転写すると、キャラの色・絵柄が**丸ごと置き換わり**、顔（目・口）と服の模様が失われた（[図](img/07-gstyle-forest1.jpg)）。「アニメ調のキャラの形と色は保ち、微細な質感・光だけ足す」という狙いとは合わない。
- 公式には**スタイルの強さを調整する引数がない**（`--path_style` と反復回数まわりだけ）。内容保持の度合いは公式コードの中の固定値で決まるため、コードを書き換えずに弱める手段がなかった。
- **自前の追試（質感成分だけを取り出して元の色に重ねる）も失敗**した（[図](img/07-gstyle-detail-transfer.jpg)）。G-Style の出力はガウシアンが分割・再配置されて（24.4万→79.0万）形状も変わっており、輝度の高周波成分を取り出して元の色に掛けても、顔が斑点状に崩れ、「汚れ」に見える。微細な質感ではなかった。
- 結論として、**G-Style は「シーン全体の絵柄を変える」用途のもの**。このプロジェクトでは次のように位置づける:
  - キャラの質感付与には使わない（質感は、メッシュ側のテクスチャ/法線・粗さの精細化、または Frosting のようなメッシュ連動の細かいガウシアン層で足すほうが筋がよい）。
  - 背景とキャラの絵柄の統一にも、そのままは使えない（背景にかけると背景の精細さが失われる見込み。未検証）。

## 2. 手順（再現可能）

1. データ: `scripts/blender/render_char_dataset.py` で144視点（T5の照明）、`scripts/gaussian/flatten_colmap_dataset.py` で黒背景に合成、`write_colmap_bin.py` で COLMAP の .bin に変換。
2. 環境: `scripts/wsl/setup_gs_envs.sh`、`build_gs_ext.sh`（venv `gstyle`、`open_clip_torch`、torch 2.8.0）。G-Style のリポジトリは submodule を持たないため、Inria 公開の `diff-gaussian-rasterization` と `simple-knn` を `~/ext/g-style/submodules/` に取得してビルド（公式README相当）。
3. 学習: `scripts/wsl/run_gstyle_char.sh style_forest1`
   - ① 素の3DGSを学習（G-Style リポジトリの `train_original.py`、30000反復）: 10分11秒、24.4万ガウシアン、テスト視点 PSNR 39.88 dB。**SH0**（視点依存の色なし）で出力された。
   - ② G-Style（`train.py --resolution 1 --starting_iter 30000 --path_style forest1.png`）: 2160反復の再最適化＋色合わせ。**51分18秒**（約1.1秒/反復。CLIP と VGG の特徴量を毎反復使う）。出力は 79.0万ガウシアン。
4. 描画: `scripts/blender/run_scene_char_ply.ps1`（T5の統合シーンに、メッシュの代わりにキャラの3DGSを置いて KIRI で描画）。

## 3. 結果

| 項目 | 内容 |
|---|---|
| 色 | 平均RGBが (0.62, 0.55, 0.46) → (0.77, 0.75, 0.63) と明るい白寄りに。スタイル画像の色調に引かれた |
| 不透明度 | 平均 0.43 → 0.60（実体が濃くなり、元の絵柄を覆った） |
| 見た目 | 顔・服の柄が消え、森の葉・花のような模様が服全体に出る（[図](img/07-gstyle-forest1.jpg)）。背景とは「別の絵柄」になる |
| 詳細層の追試 | strength 1.0 / 2.0 とも顔が崩れる（[図](img/07-gstyle-detail-transfer.jpg)） |
| 2つ目のスタイル（背景の苔のクロップ） | 実行したが、1つ目の結果で結論が出たため途中で打ち切り（約40分の節約） |

## 4. つまずきと対処（公式コードは書き換えていない）

GaussianShader と同じ（[07-gaussianshader.md](07-gaussianshader.md) の4章）。追加で:

| 問題 | 対処 |
|---|---|
| `submodules/` がない（公式リポジトリはsubmoduleのURLがgitlab.inria.fr） | Inria公開のリポジトリを `submodules/` に取得 |
| `open_clip_torch` を入れると torch が 2.14（cu130）に上がり環境が壊れる | `-c constraints.txt`（torch==2.8.0）で固定 |
| 公式の `--resolution` を指定しないと 1.6k幅まで縮める | `--resolution 1`（元の1024²）を指定 |

## 5. 今後に持ち帰ること

- 質感を足す方針は、スタイル転写（絵柄ごと置換）より、**属性を分けて足す**ほうが筋がよい: 法線・粗さ・鏡面（GaussianShader の考え方）、または Frosting のメッシュ連動の細かい層。
- 絵柄の統一を試すなら、「色は保ち、輝度の局所コントラスト（テクスチャ強度）だけをスタイル画像の統計に合わせる」ような**制約付きの自前実装**にする。今回の詳細層の追試は、形状が変わった出力を使ったので失敗した。元の形状のまま色だけ最適化する形（自前で最適化ループを書く）は、未検証の候補。

## 6. ファイル

| パス | 内容 |
|---|---|
| `scripts/wsl/run_gstyle_char.sh` | 素の3DGS学習＋G-Style |
| `scripts/gaussian/style_detail_transfer.py` | 【自前】質感成分だけを元の色に重ねる追試 |
| `scripts/blender/render_scene_char_ply.py`、`run_scene_char_ply.ps1` | 統合シーンでキャラ3DGSを描画 |
| `docs/img/07-gstyle-forest1.jpg`、`07-gstyle-detail-transfer.jpg` | 比較図 |
| Git管理外 | `experiments/T7/runs/gstyle_forest1/`（PLY・描画一式） |
