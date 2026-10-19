# このリポジトリ用のBlender(GUI)をMCPサーバー付き(ポート9877)で起動する。
# KIRI Engine 3DGS Render は専用の拡張フォルダ(BLENDER_USER_EXTENSIONS)に導入したものを使う。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts/blender/launch_blender_mcp.ps1 [.blendファイル]
param([string]$BlendFile = "")
$blender = "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
$startup = Join-Path $PSScriptRoot "mcp_startup.py"
$env:BLENDER_USER_EXTENSIONS = Join-Path $env:LOCALAPPDATA "3DGSAnimation\blender-ext"
$blenderArgs = @("--factory-startup")
if ($BlendFile) { $blenderArgs += $BlendFile }
$blenderArgs += @("--python", $startup)
Start-Process -FilePath $blender -ArgumentList $blenderArgs
