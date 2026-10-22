#!/bin/bash
# T11: Codex CLI(ChatGPT月額プラン内の画像生成)で、5枚の元画像を参考に指定方位の顔アップ(頭と肩)の画像を1枚生成する。
# 使い方: gen_codex.sh <方位deg(0=正面,+90=キャラの左側面,180=背面,-90=キャラの右側面)> <出力フォルダ> [追加の指示]
# 出力: <出力フォルダ>/az+060.png のような名前。ログは同名の .log。
az=$1; out=$2; extra=$3
if [ "$az" -gt 0 ] && [ "$az" -lt 180 ]; then dir="Direction check: on screen her nose and body turn toward the LEFT side of the image (the camera sees the character's LEFT side)."; elif [ "$az" -lt 0 ] && [ "$az" -gt -180 ]; then dir="Direction check: on screen her nose and body turn toward the RIGHT side of the image (the camera sees the character's RIGHT side, the side opposite to image 2); the result must NOT look like a mirror of the positive-angle view."; else dir=""; fi
mkdir -p "$out"; name=$(printf "face_az%+04d" $az); outw=$(cd "$out" && pwd -W)
REF='C:\Work\3DGSAnimation\assets\reference\character'
prompt="Use the image generation tool to create ONE new image. Attached are 5 reference images of the same anime character (full-body turnaround: image 1 = front view, image 2 = left side view (camera at the character's left), image 3 = three-quarter view from the character's right front, image 4 = back view, image 5 = three-quarter view from the character's left front).
Task: render a CLOSE-UP of this exact character's head and shoulders (hair, face, hair ornaments, collar and the top of the cape/chest, cut off at the upper chest) with the camera orbited horizontally to azimuth ${az} degrees, where 0 = front view, +90 = the character's left side (like image 2), 180 = back view (like image 4), -90 = the character's right side, and positive angles mean the camera moves toward the character's left. Keep the face, eyes, eyelashes, hair strands, hair ornaments and costume exactly the same design as the references, but draw them with far more fine detail and sharpness than the references (individual hair strands, eyelash lines, iris gradients and highlights, fabric weave, gold embroidery), as if the reference were a low-resolution thumbnail of a very high-resolution painting. Framing: eye-level, long-focal-length camera (almost no perspective distortion), the head centered horizontally, the eyes at about 35% from the top, the top of the hair at about 10% from the top, the head about 55% of the image width, plain flat light gray background, same soft studio lighting, portrait 4:5 canvas, highest resolution available. ${dir} ${extra}
After generating, copy the generated image file to ${outw}/${name}.png (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' \
  -i "$REF\girl1.png" "$REF\girl2.png" "$REF\girl3.png" "$REF\girl4.png" "$REF\girl5.png" -- "$prompt" < /dev/null > "$out/$name.log" 2>&1
echo "$name done: $(ls -la "$out/$name.png" 2>&1 | tail -1)"
