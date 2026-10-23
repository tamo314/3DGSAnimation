#!/bin/bash
# T11: Codex CLI。顔アップ1枚を参考に、カメラを寄せて指定の部位だけを大きく写した画像を生成する(入力解像度を上げる試み)。
# 使い方: gen_codex_zoom.sh <入力画像> <出力パス.png> <倍率> "<写す範囲の説明(英語)>"
in=$1; out=$2; z=$3; region=$4; outw=$(cd "$(dirname "$out")" && pwd -W)/$(basename "$out"); inw=$(cd "$(dirname "$in")" && pwd -W)/$(basename "$in")
prompt="Use the image generation tool to create ONE new image. Image 1 is a head-and-shoulders close-up of an anime character. Task: render the SAME picture as if the camera had moved closer by a factor of ${z} (a pure zoom-in, no change of viewing angle or pose), so that the frame shows only: ${region}. Everything must stay identical to image 1: the same drawing, the same lines, the same positions relative to each other, the same colors, lighting and style; do not redesign, do not mirror, do not change the expression. Because the camera is closer, draw the finest details sharply at the higher resolution: individual hair strands, eyelashes, iris patterns, highlights, skin shading. Portrait 4:5 canvas, highest resolution available, plain background where background shows.
After generating, copy the generated image file to ${outw} (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$inw" -- "$prompt" < /dev/null > "${out%.png}.log" 2>&1
echo "done: $(ls -la "$out" 2>&1 | tail -1)"
