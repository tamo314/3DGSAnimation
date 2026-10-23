#!/bin/bash
# T11: 窓入力(in_*.png)すべてを gen_codex_sr.sh で超解像(8並列)。既に出力があるものはスキップ。
# 使い方: sr_run.sh <入力フォルダ> <出力フォルダ>
I=$1; O=$2; mkdir -p "$O"; S="$(dirname "$0")"
ls $I/in_*.png | while read f; do o="$O/$(basename "$f" | sed 's/^in_/sr_/')"; [ -s "$o" ] || echo "$f $o"; done | xargs -P 8 -L 1 bash -c 'bash '$S'/gen_codex_sr.sh $0 $1'
echo sr done
