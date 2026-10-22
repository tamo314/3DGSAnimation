#!/bin/bash
# T11: 連鎖生成。隣の方位の顔アップ画像を参考に、カメラだけを数度回した顔アップを1枚生成する(Codex CLI)。
# 使い方: gen_codex_chain.sh <目標の方位> <隣の画像> <隣の方位> <出力フォルダ> [追加の指示]
#   方位: 0=正面, +=カメラがキャラの左へ回る(画面上でキャラが画像の左を向く), -=右。出力: <出力フォルダ>/face_az+010.png のような名前。
az=$1; nb=$2; nbaz=$3; out=$4; extra=$5; mkdir -p "$out"; name=$(printf "face_az%+04d" $az)
nbw=$(cd "$(dirname "$nb")" && pwd -W)/$(basename "$nb"); outw=$(cd "$out" && pwd -W)
anchor='C:\Work\3DGSAnimation\experiments\T11\gen\faces_all\face_az+000.png'
R='C:\Work\3DGSAnimation\assets\reference\character'
step=$((az - nbaz)); if [ $step -gt 0 ]; then dir="the camera moves further toward the character's LEFT, so on screen the character turns more toward the LEFT side of the image"; else dir="the camera moves further toward the character's RIGHT, so on screen the character turns more toward the RIGHT side of the image"; fi
prompt="Use the image generation tool to create ONE new image. Attached images: image 1 = the same character's head-and-shoulders close-up at camera azimuth ${nbaz} degrees (the neighbouring view you must continue from); image 2 = the same character's close-up at azimuth 0 (front, detail and style anchor); image 3 = full-body front view; image 4 = full-body left-side view (azimuth +90, camera at the character's left); image 5 = full-body back view (azimuth 180).
Task: render the next view of image 1: the camera orbits horizontally around the character's head by exactly ${step#-} degrees to azimuth ${az} degrees (${dir}). Everything else must stay identical to image 1: exactly the same image framing, scale and head position, the same camera height and focal length, the same gray background and soft studio lighting, and the same drawing: every hair lock, strand, braid, ribbon, flower, hair ornament, eyelash, iris, collar, cape, brooch and embroidery must look the same wherever it is still visible, with the same fine detail and sharpness. Only the viewing angle changes by that small amount; newly revealed parts (e.g. the side or back of the head) must be inferred consistently from the other images. Do not mirror anything. Portrait 4:5 canvas, highest resolution available. ${extra}
After generating, copy the generated image file to ${outw}/${name}.png (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$nbw" "$anchor" "$R\girl1.png" "$R\girl2.png" "$R\girl4.png" -- "$prompt" < /dev/null > "$out/$name.log" 2>&1
echo "$name done: $(ls -la "$out/$name.png" 2>&1 | tail -1)"
