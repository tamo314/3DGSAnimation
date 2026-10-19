# 00 環境調査（T0）

調査日: 2026-10-20 / 対象マシン: ユーザーのWindows PC（`C:\Work\3DGSAnimation`）
方針: 読み取り専用の調査のみ。ツールの導入・インストール・課金を伴うAPI呼び出しは行っていない。
APIキー等の秘密情報は変数名・設定の有無のみを記録し、値は一切記録していない。

## 1. 結論（要約）

| 区分 | 状況 |
|---|---|
| 揃っている | RTX 5060 Ti 16GB（torch 2.11+cu128でCUDA動作確認済み）、Blender 5.2.1 LTS + Blender MCPアドオン、Tripo CLI 0.3.1（V3 API・ログイン済み・残165クレジット）、Unity 6000.6.0f1、Git/Node/uv/gh/ffmpeg、WSL2 Ubuntu、十分なディスク |
| 足りない | CUDA Toolkit（nvcc）、MSVC（C++ビルドツール）、cmake、COLMAP、3DGS学習系ライブラリ（gsplat等）、KIRI Engine 3DGS Renderアドオン、IMAGE-BLASTER、World Labs / FAL のAPIキー |
| 要確認 | Claude側のBlender MCP設定（このリポジトリ用には未設定）、アドオンとMCPサーバーの版の差、KIRIアドオンのBlender 5.2対応、Unity 6000.6でのUnityGaussianSplatting動作 |

## 2. ハードウェア・OS

| 項目 | 内容 |
|---|---|
| GPU | NVIDIA GeForce RTX 5060 Ti（Blackwell, compute capability 12.0）、VRAM 16311 MiB（16GB）、TDP 180W |
| 補助GPU | AMD Radeon(TM) Graphics（CPU内蔵）。BlenderのCycles一覧にHIPデバイスとして出るため、レンダリング時はOptiXのみ選ぶこと |
| VRAM使用状況 | 調査時点でデスクトップ等が約4.7GBを使用中（実質使えるのは約11.5GB。重い学習の前に他アプリを閉じる） |
| NVIDIAドライバ | 617.14（WDDM）、`nvidia-smi` 表示のCUDA UMD 13.4 |
| CUDA Toolkit | **未導入**（`nvcc` なし、`C:\Program Files\NVIDIA GPU Computing Toolkit` なし） |
| PyTorchのCUDA | torch 2.11.0+cu128 が `cuda.is_available()=True`、デバイス名RTX 5060 Ti、capability (12, 0)（ランタイムCUDA 12.8） |
| CPU / RAM | AMD Ryzen 7 9800X3D（8コア）/ 約64GB |
| OS | Windows 11 Home 10.0.26200（64bit） |

## 3. WSL2

- WSL2あり。ディストロは `Ubuntu`（Ubuntu 26.04 LTS、カーネル 6.18.33.2-microsoft-standard-WSL2）。調査前の状態は Stopped（調査のため起動した）。
- WSL内から `nvidia-smi -L` でRTX 5060 Tiが見える（GPUパススルー可）。
- WSL内のツール: python3 3.14.4、gcc 14.3、git あり。**nvcc・cmake・uv・conda・pip3・colmap・ninja はなし**。
- WSLのルート領域: 約1TB中63GB使用、893GB空き。

## 4. 開発ツール（Windows側）

| ツール | 状況 |
|---|---|
| Python | 3.10.11（`C:\Users\tamot\AppData\Local\Programs\Python\Python310`、pyランチャーは3.10のみ） |
| pip主要パッケージ | torch 2.11.0+cu128, torchvision 0.26.0+cu128, numpy 2.2.6, scikit-image 0.25.2, ImageIO, OpenCV(cv2), Pillow。未導入: gsplat, plyfile, trimesh, open3d, bpy, fal_client, tripo3d |
| uv | 0.11.28（`uvx` も利用可） |
| conda / mamba | なし |
| Git | 2.55.0.windows.2、`gh` 2.101.0（`tamo314` でログイン済み、スコープ repo/workflow） |
| Node.js / npm | v24.18.0 / 12.0.0 |
| ffmpeg | あり（`C:\Program Files\ffmpeg-9.0-full_build-shared\bin`） |
| cmake / COLMAP | **なし** |
| MSVC（Visual Studio / Build Tools） | **なし**（vswhere・cl とも見つからず）。gsplatや diff-gaussian-rasterization をWindowsでビルドするには必要 |
| Unity | Unity Hub 3.22.3、Unity Editor **6000.6.0f1**（`C:\Program Files\Unity\Hub\Editor`） |
| グローバルnpm | tripo-cli 0.3.1, @google/gemini-cli 0.50.0, @openai/codex 0.163.0, @higgsfield/cli 1.1.26 |

## 5. Blender

- インストール: `C:\Program Files\Blender Foundation\Blender 5.2`（**Blender 5.2.1 LTS**、ビルド日 2026-08-25、同梱Python 3.13.13）。**これ1つのみ**（Steam版・別版・PATH上のblenderなし）。
- ユーザー設定: `%APPDATA%\Blender Foundation\Blender\5.2`
- 有効アドオン（ユーザー設定読み込み時）: `blender_mcp`、および標準の cycles, io_scene_fbx, io_scene_gltf2, io_anim_bvh, io_curve_svg, io_mesh_uv_layout, pose_library, bl_pkg。
- Cycles: OptiX/CUDAともにRTX 5060 Tiを認識。

### Blender MCP

- **Blenderアドオン側**: `scripts\addons\blender_mcp.py`（"MCP for Blender"、作者表記 ahujasid、**アドオン版 1.6**）が導入済みで、有効化もされている。
- **Claude側のMCP設定**（`~/.claude.json` を確認）:
  - このリポジトリ（`C:/Work/3DGSAnimation`）には **MCPサーバー未設定**。ユーザー全体の設定は `audio-studio` のみ。
  - 別プロジェクト `C:/Work/CatAnime` に `blender`（`uvx blender-mcp==1.9.1`、`DISABLE_TELEMETRY=true`）の設定がある。`C:/Windows/System32` 配下のプロジェクトにも `uvx mcp-for-blender` の設定があるが、こちらは偶発的なものとみられる。
  - アドオン1.6とサーバー1.9.1は版が離れている。Blender 5.2での動作を含め、接続テストは未実施（後続スレッドで確認）。

### KIRI Engine 3DGS Render アドオン

- **未導入**（Blenderのユーザーアドオン・拡張機能、有効アドオン一覧、`C:\Work` 配下のフォルダ名検索のいずれにも見当たらない）。
- 対応状況（GitHubのREADME・リリース・issueを確認、2026-10-20時点）:
  - 最新は **v5.1.0**（2026-08-26頃）。「Blender 5.2対応」を明記し、Windowsのクリーンインストールで Blender 5.1.1 / 5.2.0 LTS の動作確認済み。**manifestの最低要件は Blender 5.1.0** なので、導入済みの5.2.1 LTSで使える見込み（5.2.1での実機確認は未実施）。
  - 配布は Blender Extensions ではなく GitHub Releases のzip。解凍せず、Preferences → Get Extensions → Install from Disk で入れる。同梱wheelはPython 3.13（Blender 5.2のPythonと一致）。
  - 入力は3DGSの **`.ply`**。**SPZの記載はない**。
  - モードはEdit（メッシュ編集）とRender（ビューポート／オフライン描画、Blenderのメッシュと合成可）。ライティング（Sun/Spot/Area/Pointのリライティング、メッシュへの近似影、World/HDRIの拡散照明）は**すべて実験的**で、公式に「artistic approximation」とされる。
  - 既知の問題: LichtFeld Studioで30000回学習したPLYのコントラストが過大になる未解決バグ（#66）。複製ごとにGPUメモリが増える。KIRI社は定期保守から撤退しコミュニティ主導（サポート保証なし）。
  - ライセンスはGPL-2.0。

## 6. Tripo

- 導入物: **`tripo-cli` 0.3.1**（npmグローバル、`vast-enterprise/Tripo-API-CLI`）。`tripo3d` Python SDKは未導入。
- API世代: CLIは **Tripo V3 API**（`openapi.tripo3d.ai`、リージョン ov）を使用。履歴のエンドポイントも `/v3/generation/image-to-model` と `/v3/generation/text-to-image` のみで、**2026-10-31に終了するAPI v2は使っていない**（影響なし）。
- `~/.tripo` の中身: `config.json`（プロファイル `default` を有効化、APIキーはCLIのプロファイルに保存済み。値は記録しない）、`device-id`、`history.jsonl`（21タスク分の履歴）。
- `tripo doctor`: すべてOK（node, APIキー, API疎通）。残クレジット **165**（凍結0）。
- 過去履歴（2026-09-06〜2026-10-07）: image_to_model 成功12 / queued 6、text_to_image 成功2 / queued 1。履歴上の消費は計430クレジット。
- 備考: `C:\Work\3DAssetCreateWorkflow`（`.tripo`、`blender`、`specs` などを持つ別リポジトリ）に過去の3Dアセット生成ワークフローがある。参考にできるが、CLAUDE.mdの方針どおり既存コードは改変せず、参考にとどめる。

## 7. 外部サービスのAPIキー（有無のみ）

| サービス | 状況 |
|---|---|
| Tripo | 環境変数なし。ただしCLIのプロファイルにキーが保存済みで、`tripo doctor` で有効を確認 |
| World Labs（`WLT_*` / `WORLDLABS*` / `MARBLE*` など） | 環境変数は未設定。ただしユーザー指示により `apikey/worldlab.txt`（32バイト）にキーがある |
| FAL（`FAL_KEY` など） | 環境変数は未設定。ただし `apikey/fal.txt`（72バイト）にキーがある |
| `apikey/` の扱い | リポジトリ直下。`.gitignore` がないため、コミット事故を防ぐ目的でこのPCの `.git/info/exclude` に `apikey/` を追加済み（リポジトリには含まれない）。中身は読んでいない。ファイル作成時は必ず除外されていることを確認すること |
| 参考 | 上記以外では `ELEVENLABS_API_KEY` が設定されている（このプロジェクトでは未使用） |

## 8. IMAGE-BLASTER

- **未導入**。`C:\Work` 配下の検索でも見つからない。実体はGitHubリポジトリ `neilsonnn/image-blaster`（MIT）で、「単一画像から3D環境・SFX・メッシュを作るClaude Code用スキルセット」。cloneして `claude` を起動して使う。
- 必要なもの: Claude Code、World LabsとFALのAPIキー（`.env.example` あり、キーは `apikey/` にある）、画像を `input/` に置く。環境はWorld Labs marble-1.1、3DモデルはFAL経由のhunyuan-3d。生成はクラウド側で行われローカルGPU要件の記載はないが、**有料API課金が発生する**（料金は未確認）。
- 出力: 環境は **`.spz`**、モデルは `.glb` / `.obj`。KIRIアドオンは `.ply` のみなので、**SPZ→PLY変換が必要になる可能性が高い**（変換ツールは未確認。Phase 1/3の最初に要検証）。

## 9. ディスク

| ドライブ | 使用 | 空き |
|---|---|---|
| C: | 1239.1 GB | **620.7 GB** |
| D: | 746.0 GB | 185.5 GB |
| E: | 1369.2 GB | 535.3 GB |

リポジトリはC:。3DGSの学習データ・出力は数十GB規模になり得るが、Cの空きで十分。

## 10. リポジトリの現状

- リモート: `https://github.com/tamo314/3DGSAnimation.git`、`main` は `Initial commit`（440f307）1つ。`.gitignore` なし。
- 未追跡: `CLAUDE.md`、`assets/`。空ディレクトリ `docs/ experiments/ scripts/ tests/ unity/ assets/blender/` が存在（Gitは空ディレクトリを追跡しない）。`README.md` は見出し1行のみ。
- `assets/reference/`:
  - `background/forest1.png`〜`forest5.png`: 各1448×1086 RGB PNG（約3.3〜3.7MB）
  - `character/girl1.png`〜`girl5.png`: 各1122×1402 RGB PNG（約1.9〜2.1MB）
- `CLAUDE.md` の要点: 目的は「アニメ調デフォルメのキャラ・背景を、のっぺりしたトゥーンではなく微細な質感・光で表現する3DGSアニメーション/ゲームの研究」。構成は Tripo CLI（モデリング）→ Blender（調整・リギング・PBR）→ 3DGS（背景・表面描画）→ Proxy Mesh（アニメ・衝突）→ Unity（実行、aras-p/UnityGaussianSplatting）。開発ルールは、既存研究コードは参考にとどめて独自実装、Blender操作は再現可能なPython、実験結果と失敗理由を `docs/` に記録、テストはマイルストーン単位のみ。

## 11. 不足しているもの・推奨手順（未実施。要ユーザー判断）

| 優先 | 項目 | 理由 | 推奨手順 |
|---|---|---|---|
| 高 | CUDA Toolkit 12.8（Windows、または WSL） | gsplatや3DGS学習CUDAカーネルのビルドに `nvcc` が必要。torchのcu128に合わせる | WSLのUbuntuに入れるのが楽（apt/NVIDIA公式のWSL用ネットワークインストーラ）。Windowsならインストーラ版12.8 |
| 高 | MSVC Build Tools（C++デスクトップ開発） | WindowsでCUDA拡張をビルドする場合に必須 | Windowsで学習するなら導入。WSLで学習するなら不要 |
| 高 | 3DGS学習環境の場所の決定 | Windows（MSVC+CUDA）かWSL（gcc+CUDA）かで準備が変わる | **推奨: WSL2 Ubuntuで学習・評価、Windows側でBlender/Unity**。WSL内では `uv` + Python 3.12系の仮想環境、torch cu128（Blackwell対応）を作る |
| 高 | World Labs / FAL のAPIキーの渡し方 | キーは `apikey/*.txt` にある。IMAGE-BLASTERは `.env` で受け取る | 背景生成スレッドが `apikey/` から `.env`（gitignore対象）に転記して使う。値はログ・チャット・コミットに出さない |
| 高 | IMAGE-BLASTERのclone | 背景生成（Phase 1）の本体 | `neilsonnn/image-blaster` を `C:\Work` 配下かリポジトリ外にclone（Bun/Node系のビューアあり） |
| 高 | SPZ→PLY変換の手段 | blasterの出力はSPZ、KIRIはPLYのみ | 独自実装（SPZは公開仕様）か既存ツールを参考に変換スクリプトを書く |
| 中 | cmake / COLMAP | 写真/多視点からのポーズ推定が必要になる場合 | `winget install Kitware.CMake`、COLMAPは公式バイナリ（CUDA版） |
| 中 | Claude側のBlender MCP設定（このリポジトリ用） | 現状は別プロジェクトにのみ設定 | プロジェクトの `.mcp.json` に `uvx blender-mcp==1.9.1` を追加し、Blender側アドオンの版との接続テストを行う（必要ならアドオンを更新） |
| 中 | KIRI Engine 3DGS Render アドオン v5.1.0 | Phase 3でBlenderに3DGSを取り込む。5.2 LTS対応は確認済み | GitHub Releasesのzipを解凍せず Install from Disk で導入（導入は後続のBlender基盤スレッドで実施） |
| 低 | Python 3.12系、`bpy`モジュール、trimesh/plyfile/open3d | 後続スクリプト用。システムPythonは3.10 | プロジェクト専用の `uv` 環境を作って入れる（システムPythonは触らない） |

## 12. 後続スレッドを始めるための条件

- **Blender基盤スレッド**: すぐ開始可能（Blender 5.2.1 + MCPアドオンあり。MCPサーバー設定と接続確認を最初のタスクにする。Python（bpy）の再現可能スクリプトはBlenderヘッドレスで実行可）。
- **Tripo生成スレッド**: すぐ開始可能（V3 CLIログイン済み、残165クレジット。生成は課金されるので実行前にクレジット消費の確認が必要）。
- **背景生成スレッド**: APIキーは `apikey/` にあり揃っている。IMAGE-BLASTERのclone・セットアップと、有料API課金の確認が先に必要。ローカルの3DGS学習をするなら、先にWSL2にCUDA Toolkit + ビルド環境（上記の高優先）が必要。
- **Unity取り込み**: Unity 6000.6.0f1あり。`unity/` は空で、UnityGaussianSplatting（aras-p）の取り込みと6000.6での動作確認は未実施。
