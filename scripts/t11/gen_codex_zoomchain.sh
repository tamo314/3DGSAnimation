#!/bin/bash
# T11: Codex CLI。連鎖生成した顔アップ(目的の方位)を元に、カメラを寄せた部位アップを生成する。隣の方位の部位アップを、細部の見本として一緒に渡す(部位アップどうしの一貫性を保つため)。
# 使い方: gen_codex_zoomchain.sh <目的方位の顔アップ> <隣の方位の部位アップ> <出力パス.png> <倍率> "<写す範囲(英語)>"
face=$1; nb=$2; out=$3; z=$4; region=$5
w() { echo "$(cd "$(dirname "$1")" && pwd -W)/$(basename "$1")"; }
outw=$(w "$out"); facew=$(w "$face"); nbw=$(w "$nb")
prompt="Use the image generation tool to create ONE new image. Image 1 = a head-and-shoulders close-up of an anime character at some camera azimuth (the TARGET view: its pose, drawing and composition are authoritative). Image 2 = a zoomed-in detail crop of the same character from a slightly different, neighbouring camera angle (the DETAIL REFERENCE: use it only to keep the fine drawing identical: eyelash shape and count, iris pattern, highlights, eyebrow, hair strand layout, skin shading). Task: render image 1 as if the camera had moved closer by a factor of ${z} (pure zoom-in, no change of viewing angle), so that the frame shows only: ${region}. The result must match image 1 in pose, layout and colors, and match image 2 in the fine detail style, scale, framing and sharpness. Do not mirror anything or change the expression. Draw the finest details sharply: individual hair strands, eyelashes, iris patterns, highlights, skin shading. Portrait 4:5 canvas, highest resolution available.
After generating, copy the generated image file to ${outw} (PNG) and reply with only the saved path."
codex exec --skip-git-repo-check -C 'C:\Work\3DGSAnimation-T11' -i "$facew" "$nbw" -- "$prompt" < /dev/null > "${out%.png}.log" 2>&1
echo "$(basename "$out") done: $(ls -la "$out" 2>&1 | tail -1)"
