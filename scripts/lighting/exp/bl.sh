#!/bin/bash
# usage: experiments/T5/bl.sh <script.py> [args after --]
export BLENDER_USER_EXTENSIONS="$LOCALAPPDATA/3DGSAnimation/blender-ext"
s="$1"; shift
"/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" --factory-startup -b --python "$s" -- "$@"
