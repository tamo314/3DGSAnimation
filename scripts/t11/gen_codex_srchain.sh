#!/bin/bash
# T11: 窓画像の超解像を隣の視点の超解像結果を参考にして行う(連鎖)。細部(髪の筋・虹彩・まつ毛・レース)を隣と揃える。
# 使い方: gen_codex_srchain.sh <今回の入力(ぼけ)> <隣の超解像結果> <出力.png> <今回の方位> <隣の方位>
in=$1; prev=$2; out=$3; az=$4; paz=$5; w() { echo "$(cd "$(dirname "$1")" && pwd -W)/$(basename "$1")"; }; outw=$(w "$out"); inw=$(w "$in"); pw=$(w "$prev")
prompt="Use the image generation tool to create ONE new image. Image 1 is a blurry, upscaled crop of an anime character illustration (view azimuth ${az} degrees). Image 2 is the already-sharp version of the neighbouring view of the same crop window (azimuth ${paz} degrees, the head is turned by only 10 degrees between them). Task: re-render image 1 at full sharpness and resolution as a pixel-aligned restoration: keep the composition, every shape, line and highlight of image 1 at EXACTLY the same position and size (no zoom, no shift, no redesign, no mirroring, do not copy the pose of image 2), and add the fine detail the blur hides. For every surface that is visible in both images (hair strands and locks, iris pattern, eyelashes, eyebrow, lace, embroidery, skin highlights), reproduce the SAME fine detail as image 2, so that the two views are consistent with each other. Same colors and lighting as image 1. Portrait 4:5 canvas, highest resolution available.
After generating, copy the generated image file to ${outw} (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$inw" -i "$pw" -- "$prompt" < /dev/null > "${out%.png}.log" 2>&1
echo "$(basename "$out") done: $(ls -la "$out" 2>&1 | tail -1)"
