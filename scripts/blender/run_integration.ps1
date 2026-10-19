# 統合シーンをヘッドレスで再現する(.blend保存 + 5視点描画)。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_integration.ps1 [-Out experiments/T4/headless] [-Scale 1.0]
param([string]$Out = "experiments/T4/headless", [string]$Scale = "")
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
$extra = @()
if ($Scale) { $extra = @("--scale", $Scale) }
& $blender --factory-startup -b --python scripts/blender/run_integration.py -- --out $Out @extra
Pop-Location
