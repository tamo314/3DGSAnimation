# 10 背景3DGSの直接生成（T1）結果

実施日: 2026-10-20 / ブランチ: `claude/T1-background` / 環境: Windows 11、RTX 5060 Ti
目的: forest1.png から、キャラを置ける小さな森の広場を、視点移動に耐える3DGSとして得る。ランドマーク整理は [10-background-landmarks.md](10-background-landmarks.md)。

## 1. 結論

- **採用**: World Labs `marble-1.1`（標準）で、forest1原画 + 自前プロンプトから生成した世界 `forest_clearing`。
  生成回数は **3回**（上限5回のうち draft 2回 + 標準1回）。消費は計 2040クレジット（約 $1.6）。残り 4960クレジット。
- 保存: `assets/generated/background/forest_clearing_{full_res,500k,100k}.spz`、`forest_clearing_{full_res,500k}.ply`、コライダーGLB、パノラマ。メタは `assets/generated/background/world_meta.json`。
  大きなバイナリはGit管理外（メインのフォルダ側にだけある）。
- **PLYはWorld Labsから直接取得できる**（`:export`、無料）。SPZ→PLY変換は不要だった（変換器 `scripts/gaussian/spzply.py` は他ソース向けの保険）。
- 見た目: 元カメラ周囲 ±3m の範囲で、古木・石造アーチ・小道・滝と池・木漏れ日（光芒）・青い小花が高精細に残る。広場の足元は平坦。
- 限界: 視点が木や岩壁に近づくと幾何の内側に入る。元カメラから7m以上後退・6m以上の横移動は破綻する（4章）。
- `500k` は `full_res`（192万）と見た目がほぼ同じで、容量は 7.9MB（full_res は 30MB）。**実用はまず500kを推奨**。SH次数は0（視線による色変化なし）。

## 2. 実験の記録

| ID | モデル | 入力 | 消費 | 結果 |
|---|---|---|---|---|
| d1 | marble-1.0-draft | forest1 + 自動キャプション | 230 | 構図はほぼ再現するが、全体にぼけ。自動キャプションが「遺跡が輪になった360度の聖域」という別の描写になり、広場の足元が荒れる（[画像](img/10-background-draft1-autocaption.jpg)） |
| d2 | marble-1.0-draft | forest1 + 自前プロンプト（`experiments/prompts/forest1_clearing_v1.txt`、再キャプションなし） | 230 | 足元が平坦で開けた広場になり、光芒も強い。→ 採用（[画像](img/10-background-draft2-prompt.jpg)） |
| g3 | **marble-1.1** | d2と同じ | 1580 | 解像感・質感が大幅に向上。ランドマークがすべて残る。→ **採用**（[画像](img/10-background-final-5views.jpg)） |

各回の詳細（操作ID、クレジット前後、世界ID）は `experiments/T1-*/meta.json`。

draftは構図と足元の確認には使えるが、質感は別物（ぼけが強い）なので、仕上がりの判断は標準モデルでしかできない。draftは1回230、標準は1580。

## 3. 破綻検査の方法

- 確認用ビューア（自作、three.js + Spark 2.0.0）: `tools/viewer/index.html`、サーバ `scripts/background/viewer_server.py`。
- 撮影: `tools/capture/capture.mjs`（ヘッドレスChrome、5視点を連続撮影）。コンタクトシート `scripts/background/contact_sheet.py`。
- 座標: SPZ（RDF）をX軸180度回転 → メートル換算（`metric_scale_factor`）→ 地面合わせ（`ground_plane_offset`）。
- 視点の距離測定: `tools/capture/rayprobe.mjs`（元カメラからレイを飛ばして最初の不透明面までの距離）。

## 4. 視点移動の破綻

視点は `scripts/background/camera_paths_background.json`（Blender座標、T3形式）の5つ。すべて破綻なく見られる（[画像](img/10-background-final-5views.jpg)）。

| 視点 | 結果 |
|---|---|
| front_wide（元カメラ、高さ1.0m） | 元画像の構図をほぼ再現 |
| character_medium（右へ1.2m・前へ1m、高さ0.9m） | 地面・池・古木の根が連続。良好 |
| dappled_low（高さ0.3mから見上げ） | 光芒・樹冠・青空が破綻なし。この世界で最も見映えがよい視点 |
| side_depth（左へ2m・後ろへ0.5m） | アーチの側面と木々の視差が保たれる |
| high_oblique（高さ4mの俯瞰） | 池の水面が透過気味、最奥の岩肌に伸びが出るが許容 |

### T3の仮定義の視点（`scripts/gaussian/camera_paths.json`）は、この世界では使えなかった

T3の想定（キャラの7m後方、6m横、アーチは8m先）に対し、この世界の自由空間はずっと狭い。
キャラ足元を元カメラの前方3mに置くと front_wide（7m後方）は背後の古木の内側、side_depth（6m横）は右の大木の内側に入って撮れない（[画像](img/10-background-t3paths-charY3.jpg)）。
前方8mに置くと近景が荒れ、ローアングルは岩に埋まる（[画像](img/10-background-t3paths-charY8.jpg)）。
生成の失敗ではなく、**視点配置が世界の寸法と合っていない**ためなので、世界に合わせて詰め直した（上記の5視点）。
測定: アーチは元カメラの約23m先、高さ約10m、大木は右9.5m・左12m。T3の想定（アーチ8m先・高さ3.2m）の約3倍の巨大な世界になる。

## 5. 失敗・つまずき（再発防止のため記録）

- 最初の生成リクエストが 422: `is_pano` に文字列 `"false"` を渡した（正しくは真偽値）。課金は発生せず、回数にも数えない。スクリプトは送信失敗時に何も記録しない。
- Git Bash が引数の `/gen/...` を `C:/Program Files/Git/gen/...` に書き換え、ビューアが404になった。相対パス `gen/...` で渡す。
- ビューアのブラウザペインが非表示だと `requestAnimationFrame` が止まり描画されない。撮影はヘッドレスChrome（Playwright）に切り替えた。
- 最初の視点は元カメラの高さ1.5m・距離7m前提で作ったため、draftでは視点が地面の下や木の中に入った。draftはメートル換算が無く、元カメラ高さが約0.45単位しかなかったため。標準モデルで返る `metric_scale_factor` / `ground_plane_offset` を使うと整合した（draftは `semantics_metadata` が null）。
- コライダーGLBの頂点から広場を自動探索する案は、頂点が約8万点で広範囲に疎なため情報が足りず断念した。キャラ位置の確定はBlender側での確認に任せる。
- 日本語のCLI引数は、実行環境によっては文字化けしてメタに保存される。`experiments/*/meta.json` の `label` は手で直した。

## 6. 次にやること・判断が要る点

- キャラ位置（暫定: 元カメラの前方3.5m、小道の上）をBlender/KIRIで確定する。
- 世界のスケール: このままだと「アーチ10m・視点高1m」の巨大な世界。デフォルメキャラ（1m）との見た目は、Blender上で `scale` を決めれば調整できる。
- もっと広く歩かせたい場合は、別の入力画像を足した生成か、標準 `marble-1.1-plus`（1580〜3080クレジット）で試す。残り枠は2回。
