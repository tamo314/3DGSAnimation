# T7: 統合シーンにキャラ3DGS(PLY)を置いて描画。使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_scene_char_ply.ps1 -CharPly <ply> -Out <dir> -Tag m_ [-Cams front_wide,...] [-Extra --keep-mesh]
param([string]$CharPly, [string]$Out, [string]$Tag = "", [string]$Cams = "", [string[]]$Extra = @())
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
$a2 = @("--char-ply", $CharPly, "--out", $Out, "--tag", $Tag)
if ($Cams) { $a2 += @("--cams", $Cams) }
& $blender --factory-startup -b --python scripts/blender/render_scene_char_ply.py -- @a2 @Extra
Pop-Location
