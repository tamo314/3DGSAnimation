#!/bin/bash
# T11: 窓の超解像を方位0から ±10°ずつ連鎖で作る。使い方: srchain_run.sh <窓入力フォルダ> <起点(方位0の超解像)> <出力フォルダ> <窓名> <+1|-1> <最大方位>
I=$1; seed=$2; O=$3; nm=$4; dir=$5; max=$6; mkdir -p "$O"; S="$(dirname "$0")"
prev=$seed; paz=0; az=0
while true; do
  az=$((az + dir*10)); [ ${az#-} -gt $max ] && break
  t=$(printf "%+04d" $az); o="$O/sr_${nm}_az$t.png"
  [ -s "$o" ] || bash $S/gen_codex_srchain.sh "$I/in_${nm}_az$t.png" "$prev" "$o" $az $paz || true
  [ -s "$o" ] || bash $S/gen_codex_srchain.sh "$I/in_${nm}_az$t.png" "$prev" "$o" $az $paz
  [ -s "$o" ] || break
  prev=$o; paz=$az
done
echo "chain $nm $dir done"
