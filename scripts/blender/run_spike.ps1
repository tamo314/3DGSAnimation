# ヘッドレスBlenderでスパイク実験を実行する。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/run_spike.ps1 -Exp basic [-Out experiments/spike/out]
param([string]$Exp = "basic", [string]$Out = "experiments/spike/out", [string]$Extra = "")
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
Push-Location $repo
& $blender --factory-startup -b --python scripts/blender/spike_kiri.py -- --exp $Exp --out $Out $Extra.Split(" ", [StringSplitOptions]::RemoveEmptyEntries)
Pop-Location
