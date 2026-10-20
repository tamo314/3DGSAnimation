# T8: 超解像テクスチャで差し替えて、マスター(2048², 288視点)・拡大評価・下半身評価を描き直す(既に描いた枚数は飛ばす)。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_hq_master_sr.ps1 -Tex experiments/T8/sr/tex/basecolor_sr_anime6b_8k.png -Tag sr8k
param([string]$Tex, [string]$Tag = "sr8k")
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
$o = "experiments/T8/master_$Tag"
& $blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out $o --size 2048 --basecolor $Tex
& $blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out "${o}_zoom" --size 2048 --preset zoom --basecolor $Tex
& $blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out "${o}_lower" --size 2048 --preset lower --basecolor $Tex
Pop-Location
