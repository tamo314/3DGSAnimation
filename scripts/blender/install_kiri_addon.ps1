# KIRI Engine 3DGS Render をこのプロジェクト専用の拡張フォルダへ導入する(約770MB、Gitには入れない)。
# ユーザー共通のBlender設定やCatAnime等の他プロジェクトのBlenderには影響しない。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/install_kiri_addon.ps1
param([string]$Version = "v5.1.0")
$ErrorActionPreference = "Stop"
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$dl = Join-Path $env:TEMP "kiri-addon-$Version"
New-Item -ItemType Directory -Force $dl | Out-Null
$zip = Join-Path $dl ("3dgs_render_by_kiri_engine_" + $Version.TrimStart("v") + ".zip")
if (-not (Test-Path $zip)) {
    gh release download $Version -R Kiri-Innovation/3dgs-render-blender-addon -p (Split-Path $zip -Leaf) -D $dl
}
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
New-Item -ItemType Directory -Force $env:BLENDER_USER_EXTENSIONS | Out-Null
& $blender --factory-startup -b --command extension install-file -r user_default $zip
