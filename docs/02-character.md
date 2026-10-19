# 02 キャラクター生成（T2）

日付: 2026-10-20 / 実験記録: `experiments/char-t2-01/meta.json`

## 結論
- 参照画像の前・左・背面の3枚を Tripo V3.1 のマルチビューに入力し、**1回目の生成で採用可能な品質**が得られた（消費40クレジット、残165→125。タスク使用1/3）。
- 杖・鞄・フラスコ・ベルト・マント裏・髪型（編み込み、アホ毛）・顔・手・ブーツ裏すべて大きな破綻なし。杖を別パーツで作り直す必要はなかった。

## 手順（再現可能）
1. `scripts/character/preprocess_refs.py`: rembgで背景除去し、3視点を縮尺不変で1397x1397に統一
   - girl1=正面、girl2=左側面、girl4=背面。girl3/5（斜め向き）は使わない。右側面なし（杖・鞄が左右非対称のため鏡像は使わず空欄）。
2. `tripo make front.png left.png back.png -p texture=true -p pbr=true -p texture_quality=detailed -p texture_alignment=original_image`（model v3.1-20260211）
3. `scripts/character/inspect_glb.py`: Blenderで読み込み、8方向＋顔アップをレンダリングして検査
4. `scripts/character/normalize_character.py`: 前方向=-Y、足元中心を原点・足裏Z=0、身長1.2mに正規化し GLB/.blend を出力
5. `scripts/character/make_compare.py`: 参照画像との比較画像

## 所見・失敗メモ
- TripoのGLBは **+X向き**・原点は体の中心・高さ1.0に自動正規化されていた。
- Blenderでglbを読み込んだオブジェクトは回転モードがクォータニオンのため、`rotation_euler` だけでは回らない。`rotation_mode="XYZ"` を先に設定する。
- `bpy` のレンダー出力パスは相対パスだとCドライブ直下に出てしまった。必ず絶対パスにする（スクリプトは `resolve()` 済み）。
- 約144万三角形・4K×3枚のテクスチャ（Color/NormalGL/ORM）で約53MB。ゲーム投入には軽量化が必要（今回は未実施。後続でdecimate、または3DGS化）。
- 髪の質感は少し粘土っぽく光沢が強い。PBR材質の調整はBlender側で行う想定。
