#!/bin/bash
# T11: 学習済みの run を、顔アップ(zoom 2.92)と窓A(zoom 6.56)のカメラで、学習していない方位から描き直す。
# 使い方: render_cmp.sh <run名> <tele|dist> <出力名> az1 az2 ...   (出力: experiments/T11/cmp/<出力名>/{face,winA,winB}_az+XXX.png)
run=$1; mode=$2; out=$3; shift 3
R=/mnt/c/Work/3DGSAnimation-T11/experiments/T11
tgt() { python3 - "$@" <<'PY'
import sys, math
az, sx, sy, tz = map(float, sys.argv[1:5]); a = math.radians(az)
c = (math.sin(a), -math.cos(a), 0.0); fwd = (-c[0], -c[1], 0.0)
right = (fwd[1] * 1 - 0, 0 - fwd[0] * 1, 0.0)                    # fwd x z
n = math.hypot(*right[:2]); right = (right[0] / n, right[1] / n, 0.0)
print("%f,%f,%f" % (right[0] * sx, right[1] * sx, tz + sy))
PY
}
for az in "$@"; do
  for spec in "face 2.9236 -0.004 0.0" "winA 6.5607 -0.0492 0.1497" "winB 6.5607 -0.0492 -0.0231"; do
    set -- $spec; nm=$1; z=$2; sx=$3; sy=$4; t=$(tgt $az $sx $sy 0.60178)
    f=""; [ $mode = tele ] && f="--tele"
    mkdir -p $R/cmp/$out
    bash /mnt/c/Work/3DGSAnimation-T11/scripts/t11/gs_wsl.sh gs_render.py --params $R/runs/$run/params.pt --out $R/cmp/$out --views="$az,0,${nm}_az$(printf %+04d $az)" --zoom $z --target=$t $f > /dev/null 2>&1
  done
done
