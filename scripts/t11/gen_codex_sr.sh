#!/bin/bash
# T11: Codex CLI。顔アップの一部を切り出して拡大した画像(ぼやけている)を、構図・線の位置を変えずに鮮明に描き直させる(生成AIによる超解像)。切り出し窓が既知なので、カメラ(倍率・位置)が厳密に決まる。
# 使い方: gen_codex_sr.sh <切り出して拡大した入力画像> <出力パス.png>
in=$1; out=$2; w() { echo "$(cd "$(dirname "$1")" && pwd -W)/$(basename "$1")"; }; outw=$(w "$out"); inw=$(w "$in")
prompt="Use the image generation tool to create ONE new image. Image 1 is a blurry, upscaled crop of an anime character illustration (a low-resolution crop that was enlarged). Task: re-render exactly this picture at full sharpness and resolution: keep the composition, every shape, every line and every highlight at EXACTLY the same position and size as in image 1 (a pixel-aligned restoration, no zoom, no shift, no redesign, no mirroring), and only add the fine detail that the blur hides: crisp lines, individual hair strands, eyelashes, skin shading, lip and nose highlights, sharp edges. Same colors and lighting. Portrait 4:5 canvas, highest resolution available.
After generating, copy the generated image file to ${outw} (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$inw" -- "$prompt" < /dev/null > "${out%.png}.log" 2>&1
echo "$(basename "$out") done: $(ls -la "$out" 2>&1 | tail -1)"
