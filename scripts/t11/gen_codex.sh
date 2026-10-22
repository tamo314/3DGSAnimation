#!/bin/bash
# T11: Codex CLI(ChatGPT月額プラン内の画像生成)で、5枚の元画像を参考に指定方位のキャラ画像を1枚生成する。
# 使い方: gen_codex.sh <方位deg(0=正面,+90=キャラの左側面,180=背面,-90=キャラの右側面)> <出力フォルダ> [追加の指示]
# 出力: <出力フォルダ>/az+060.png のような名前。ログは同名の .log。
az=$1; out=$2; extra=$3
if [ "$az" -gt 0 ] && [ "$az" -lt 180 ]; then dir="Direction check: on screen her nose and body turn toward the LEFT side of the image (the camera sees the character's LEFT side)."; elif [ "$az" -lt 0 ] && [ "$az" -gt -180 ]; then dir="Direction check: on screen her nose and body turn toward the RIGHT side of the image (the camera sees the character's RIGHT side, the side opposite to image 2); the result must NOT look like a mirror of the positive-angle view."; else dir=""; fi
mkdir -p "$out"; name=$(printf "az%+04d" $az); outw=$(cd "$out" && pwd -W)
REF='C:\Work\3DGSAnimation\assets\reference\character'
prompt="Use the image generation tool to create ONE new image. Attached are 5 reference images of the same anime character (full-body turnaround: image 1 = front view, image 2 = left side view (camera at the character's left), image 3 = three-quarter view from the character's right front, image 4 = back view, image 5 = three-quarter view from the character's left front).
Task: render this exact character with the camera orbited horizontally to azimuth ${az} degrees, where 0 = front view, +90 = the character's left side (like image 2), 180 = back view (like image 4), -90 = the character's right side, and positive angles mean the camera moves toward the character's left. The views between the references must be inferred consistently from them. Keep the face, hair, costume, accessories, staff, bag, boots and proportions exactly the same as the references (the staff, the bag and every asymmetric detail must stay on the same side of her body as in the references; do not mirror anything). Same standing pose, full body from head to boots, centered, same size and the same soft studio lighting, plain flat light gray background, eye-level long-focal-length camera (almost no perspective distortion), portrait 4:5 canvas, highest detail and resolution available, the same anime style with fine texture and subtle shading as the references. ${dir} ${extra}
After generating, copy the generated image file to ${outw}/${name}.png (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' \
  -i "$REF\girl1.png" "$REF\girl2.png" "$REF\girl3.png" "$REF\girl4.png" "$REF\girl5.png" -- "$prompt" < /dev/null > "$out/$name.log" 2>&1
echo "$name done: $(ls -la "$out/$name.png" 2>&1 | tail -1)"
