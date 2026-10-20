# T9: 変形後の正解(元メッシュ)をBlenderで描画。例: powershell -ExecutionPolicy Bypass -File scripts/t9/run_pose_ref.ps1 -Out experiments/T9/ref -Poses rest,lean,head -Views 0000_ring.png,0064_ring.png
param([string]$Out, [string]$Poses = "rest,lean,head", [string]$Views = "0000_ring.png", [string]$Master = "C:\Work\3DGSAnimation-T8\experiments\T8\master", [int]$Size = 1024)
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
& $blender --factory-startup -b --python scripts/t9/render_pose_ref.py -- --master $Master --out $Out --poses $Poses --views $Views --size $Size
Pop-Location
