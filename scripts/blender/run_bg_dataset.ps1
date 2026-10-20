# T7: 背景多視点データセットの描画。使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_bg_dataset.ps1 -Out experiments/T7/data/bg_scene [-Views 160] [-Width 1024] [-Height 768]
param([string]$Out = "experiments/T7/data/bg_scene", [int]$Views = 160, [int]$Width = 1024, [int]$Height = 768)
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
& $blender --factory-startup -b --python scripts/blender/render_bg_dataset.py -- --out $Out --views $Views --width $Width --height $Height
Pop-Location
