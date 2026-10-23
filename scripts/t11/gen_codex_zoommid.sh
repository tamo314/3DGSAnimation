#!/bin/bash
# T11: Codex CLI。部位アップ(寄り画像)の補間。同じ部位アップの隣り合う2つの方位(a, b)から、その中間の方位のカメラの部位アップを生成する。
# 使い方: gen_codex_zoommid.sh <方位aの部位アップ> <aの方位> <方位bの部位アップ> <bの方位> <出力パス.png> <中間の方位>
A=$1; aa=$2; B=$3; ba=$4; out=$5; mid=$6
w() { echo "$(cd "$(dirname "$1")" && pwd -W)/$(basename "$1")"; }
outw=$(w "$out"); Aw=$(w "$A"); Bw=$(w "$B")
if [ $ba -gt $aa ]; then dir="Positive azimuth means the camera moves toward the character's LEFT, so on screen the face turns more toward the LEFT side of the image as azimuth increases."; else dir="Positive azimuth means the camera moves toward the character's LEFT, so on screen the face turns more toward the LEFT side of the image as azimuth increases."; fi
prompt="Use the image generation tool to create ONE new image. Image 1 and image 2 are zoomed-in detail crops (eyes, eyebrows, nose bridge and bangs) of the same anime character, taken with the same camera zoom from two nearby horizontal camera azimuths: image 1 at azimuth ${aa} degrees, image 2 at azimuth ${ba} degrees. ${dir}
Task: render the same crop at the intermediate azimuth ${mid} degrees (exactly between the two): a view-interpolation. Keep the framing, scale and head position as the average of the two images, and keep every detail identical to the two images wherever visible: the shape and number of eyelashes, iris pattern and highlights, eyebrows, each hair strand and lock, skin shading, colors and lighting. Draw the finest details sharply, like the two inputs. Do not mirror anything and do not change the expression. Portrait 4:5 canvas, highest resolution available.
After generating, copy the generated image file to ${outw} (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$Aw" "$Bw" -- "$prompt" < /dev/null > "${out%.png}.log" 2>&1
echo "$(basename "$out") done: $(ls -la "$out" 2>&1 | tail -1)"
