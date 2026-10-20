"""MILo(公式・無改変)を WSL2 で動かすための起動シム。使い方: python milo_shim.py <公式スクリプト(例 train.py)> [引数...]  (cwd = ~/ext/MILo/milo)

WSL2 には NVIDIA の OpenGL/EGL が無く、nvdiffrast の RasterizeGLContext が使えない。MILo は MeshRasterizer を use_opengl=True 固定で呼ぶため、
公式コードは書き換えず、起動時に dr.RasterizeGLContext を CUDAラスタライザ(RasterizeCudaContext)に差し替えてから公式スクリプトを実行する。
"""
import os
import runpy
import sys

sys.path.insert(0, os.getcwd())
import nvdiffrast.torch as dr  # noqa: E402

dr.RasterizeGLContext = lambda *a, **k: dr.RasterizeCudaContext()
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
