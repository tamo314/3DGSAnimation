# T7: 背景PLYを統合シーンの5視点で描画。例: powershell -ExecutionPolicy Bypass -File scripts/blender/run_bg_ply.ps1 -Out <dir> -Tag m_ -BgPly <ply> -Sh 3
param([string]$Out, [string]$Tag = "", [string]$BgPly = "", [int]$Sh = 0, [switch]$Orig)
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
$a2 = @("--out", $Out, "--tag", $Tag, "--sh", $Sh)
if ($Orig) { $a2 += "--orig" } else { $a2 += @("--bg-ply", $BgPly) }
& $blender --factory-startup -b --python scripts/blender/render_bg_ply.py -- @a2
Pop-Location
