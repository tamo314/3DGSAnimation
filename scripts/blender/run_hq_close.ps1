# T8: 顔に寄った学習・評価用の視点(close: 距離0.40m, 40枚, k%8==0がtest)を、元テクスチャと超解像テクスチャの両方で描く。
param([string]$Tex = "experiments/T8/sr/tex/basecolor_sr_anime6b_8k.png", [string]$Tag = "sr8k")
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
& $blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out experiments/T8/master_close --size 2048 --preset close
& $blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out "experiments/T8/master_close_$Tag" --size 2048 --preset close --basecolor $Tex
Pop-Location
