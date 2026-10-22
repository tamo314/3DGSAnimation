#!/bin/bash
# T11: 3DGSの描画(ぼやけ・破綻あり)を、Codex CLIの画像生成で「構図を変えずに細部だけ鮮明に」描き直す(描き直し往復)。
# 使い方: gen_codex_refine.sh <入力画像(3DGSの描画)> <出力フォルダ> [追加の指示]   出力: <出力フォルダ>/<入力と同名>.png
in=$1; out=$2; extra=$3; mkdir -p "$out"; name=$(basename "$in" .png)
inw=$(cd "$(dirname "$in")" && pwd -W)/$(basename "$in"); outw=$(cd "$out" && pwd -W)
ref='C:\Work\3DGSAnimation\assets\reference\character\girl1.png'
prompt="Use the image generation tool to create ONE new image. Image 1 is a blurry, slightly broken render of a 3D reconstruction of an anime character (white background). Image 2 is a sharp reference of the same character (front view, for design and finish only).
Task: redraw image 1 as a crisp, clean, high-detail anime illustration, finished in the same style and fine detail as image 2. The pose, camera angle, framing, silhouette, proportions, and the position and size of every element (eyes, brows, nose, mouth, hair masses and strands, ribbon, flower, collar, cape, brooch, embroidery) must stay exactly where they are in image 1: do not move, rotate, mirror, re-pose or re-crop anything and do not add or remove elements. Only repair artifacts (smeared strands, stray fragments, blotchy skin) and add fine detail: sharp individual hair strands, clean eyelash lines, iris gradients and catchlights, fabric weave, crisp gold embroidery. Keep the plain white background and the same canvas size and aspect ratio (4:5 portrait). ${extra}
After generating, copy the generated image file to ${outw}/${name}.png (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$inw" "$ref" -- "$prompt" < /dev/null > "$out/$name.log" 2>&1
echo "$name done: $(ls -la "$out/$name.png" 2>&1 | tail -1)"
