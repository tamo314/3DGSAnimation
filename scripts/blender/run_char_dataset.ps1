# T7: キャラ多視点データセットの描画。使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_char_dataset.ps1 -Out experiments/T7/data/char_scene -Light scene [-Views 144] [-Size 1024]
param([string]$Out = "experiments/T7/data/char_scene", [string]$Light = "scene", [int]$Views = 144, [int]$Size = 1024)
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
& $blender --factory-startup -b --python scripts/blender/render_char_dataset.py -- --out $Out --light $Light --views $Views --size $Size
Pop-Location
