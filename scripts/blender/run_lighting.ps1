# T5b: ライティング適用の5視点描画。使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_lighting.ps1 -Tag e1_ [-Cams front_wide,character_medium] [-- 追加引数]
param([string]$Out = "experiments/T5/out", [string]$Tag = "", [string]$Cams = "", [string[]]$Extra = @())
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
$args2 = @("--out", $Out, "--tag", $Tag)
if ($Cams) { $args2 += @("--cams", $Cams) }
& $blender --factory-startup -b --python scripts/blender/run_lighting.py -- @args2 @Extra
Pop-Location
