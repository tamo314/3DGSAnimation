# T8: 高解像度マスターの描画。使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_hq_master.ps1 [-Out experiments/T8/master] [-Size 2048] [-Limit 0]
param([string]$Out = "experiments/T8/master", [int]$Size = 2048, [int]$Limit = 0)
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
& $blender --factory-startup -b --python scripts/blender/render_hq_master.py -- --out $Out --size $Size --limit $Limit
Pop-Location
