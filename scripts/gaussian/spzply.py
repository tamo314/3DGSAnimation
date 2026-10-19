"""SPZ <-> 3DGS PLY 変換(自前実装)。

SPZ形式(Niantic, MIT)の仕様は公開リポジトリの記述を参考にし、コードは独自に書いている。
対応: SPZ v2/v3(gzip単一ストリーム)・v4(zstd分割ストリーム。`pip install zstandard` が必要)。
v1(float16位置)は未対応。拡張(SPZ extensions)は読み飛ばし、警告のみ出す。

内部表現 `Cloud`(numpy, 全てfloat32、PLYと同じ「活性化前」の値):
  positions (N,3)   位置
  scales    (N,3)   対数スケール(log)
  rotations (N,4)   クォータニオン (w,x,y,z)  ※SPZファイル内は(x,y,z,w)
  alphas    (N,)    不透明度のlogit
  colors    (N,3)   SH DC成分 f_dc(RGB)
  sh        (N,K,3) 高次SH係数(K=0/3/8/15/24)。係数kごとにRGB
  coord     座標系名("RUB"など)。SPZ既定はRUB、3DGSのPLYはRDF。

座標系は標準ファミリ(軸の符号反転だけで変換できる8種: L/R, U/D, F/B)のみ対応。
使い方:
  python scripts/gaussian/spzply.py spz2ply in.spz out.ply [--to RDF|RUB|...]
  python scripts/gaussian/spzply.py ply2spz in.ply out.spz [--from RDF] [--version 3]
  python scripts/gaussian/spzply.py info in.spz
"""
from __future__ import annotations

import argparse
import gzip
import struct
import sys
import warnings
from dataclasses import dataclass, field

import numpy as np

NGSP_MAGIC = 0x5053474E
COLOR_SCALE = 0.15
SH_DIM = {0: 0, 1: 3, 2: 8, 3: 15, 4: 24}
SQRT1_2 = np.float32(np.sqrt(0.5))
DEFAULT_SH1_BITS = 5
DEFAULT_SH_REST_BITS = 4


@dataclass
class Cloud:
    positions: np.ndarray
    scales: np.ndarray
    rotations: np.ndarray  # wxyz
    alphas: np.ndarray
    colors: np.ndarray
    sh: np.ndarray  # (N,K,3)
    coord: str = "RUB"
    antialiased: bool = False
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.positions)

    @property
    def sh_degree(self) -> int:
        k = self.sh.shape[1]
        for d, dim in SH_DIM.items():
            if dim == k:
                return d
        raise ValueError(f"SH係数の数が不正: {k}")


# ----------------------------------------------------------------------------
# 座標系(標準ファミリ)
# ----------------------------------------------------------------------------
# 各軸の向き: x∈{R,L}, y∈{U,D}, z∈{F,B}
_AXIS_SIGN = {"R": 1, "L": -1, "U": 1, "D": -1, "B": 1, "F": -1}
# 基準(RUB)に対する符号。+x=Right, +y=Up, +z=Back。


def _sign_vector(system: str) -> np.ndarray:
    system = system.upper()
    if len(system) != 3 or system[0] not in "RL" or system[1] not in "UD" or system[2] not in "FB":
        raise ValueError(f"未対応の座標系: {system} (標準ファミリ LR/UD/FB のみ)")
    return np.array([_AXIS_SIGN[c] for c in system], dtype=np.float32)


# 3DGS式SHの各係数が x,y,z について持つ奇偶(基底関数の単項式の次数の偶奇)。
# 軸を反転すると、その軸の次数が奇数の係数は符号が反転する。
_SH_PARITY = np.array(
    [
        (0, 1, 0), (0, 0, 1), (1, 0, 0),  # 1次: y, z, x
        (1, 1, 0), (0, 1, 1), (0, 0, 0), (1, 0, 1), (0, 0, 0),  # 2次: xy, yz, 2zz-xx-yy, xz, xx-yy
        (0, 1, 0), (1, 1, 1), (0, 1, 0), (0, 0, 1), (1, 0, 0), (0, 0, 1), (1, 0, 0),  # 3次
    ],
    dtype=np.int8,
)


def convert_coordinates(cloud: Cloud, to: str) -> Cloud:
    """座標系を軸反転で変換した新しいCloudを返す(元は変更しない)。"""
    if cloud.coord.upper() == to.upper():
        return cloud
    f = _sign_vector(cloud.coord) * _sign_vector(to)  # 反転する軸は -1
    if cloud.sh.shape[1] > 15 and np.any(f < 0):
        raise ValueError("SH 4次の座標系変換は未対応")
    det = float(np.prod(f))
    pos = cloud.positions * f
    # 回転: R' = F R F(スケールは軸反転で不変)。クォータニオンのベクトル部は det(F)·F·v に変換される。
    qs = np.array([1.0, *(det * f)], dtype=np.float32)
    rot = cloud.rotations * qs
    sh = cloud.sh
    if sh.shape[1]:
        k = sh.shape[1]
        flip = np.prod(np.where(_SH_PARITY[:k] == 1, f[None, :], 1.0), axis=1).astype(np.float32)
        sh = sh * flip[None, :, None]
    return Cloud(pos.astype(np.float32), cloud.scales, rot.astype(np.float32), cloud.alphas,
                 cloud.colors, sh.astype(np.float32), to.upper(), cloud.antialiased, cloud.meta)


# ----------------------------------------------------------------------------
# SPZ 読み込み
# ----------------------------------------------------------------------------
def _unpack_streams(buf: dict, n: int, sh_degree: int, frac_bits: int, version: int) -> Cloud:
    shdim = SH_DIM[sh_degree]
    p = buf["positions"].reshape(n, 3, 3).astype(np.int32)
    fixed = p[..., 0] | (p[..., 1] << 8) | (p[..., 2] << 16)
    fixed = np.where(fixed & 0x800000, fixed | ~0xFFFFFF, fixed)  # 24bit符号拡張
    positions = fixed.astype(np.float32) / np.float32(1 << frac_bits)

    alphas_u8 = buf["alphas"].astype(np.float32) / 255.0
    with np.errstate(divide="ignore"):
        alphas = np.log(alphas_u8 / (1.0 - alphas_u8))
    alphas = np.clip(alphas, -30.0, 30.0).astype(np.float32)  # 0/255 -> ±inf を丸める

    colors = ((buf["colors"].reshape(n, 3).astype(np.float32) / 255.0) - 0.5) / COLOR_SCALE
    scales = buf["scales"].reshape(n, 3).astype(np.float32) / 16.0 - 10.0

    if version >= 3:
        comp = buf["rotations"].reshape(n, 4).astype(np.uint32)
        comp = comp[:, 0] | (comp[:, 1] << 8) | (comp[:, 2] << 16) | (comp[:, 3] << 24)
        largest = (comp >> 30).astype(np.int64)
        xyzw = np.zeros((n, 4), dtype=np.float32)
        sumsq = np.zeros(n, dtype=np.float32)
        rest = comp.copy()
        for i in (3, 2, 1, 0):
            mag = (rest & 0x1FF).astype(np.float32)
            neg = ((rest >> 9) & 1).astype(bool)
            val = SQRT1_2 * mag / np.float32(0x1FF)
            val = np.where(neg, -val, val)
            use = largest != i
            rest = np.where(use, rest >> 10, rest)  # 最大成分は格納されていないので読み進めない
            xyzw[:, i] = np.where(use, val, 0.0)
            sumsq += np.where(use, val * val, 0.0).astype(np.float32)
        xyzw[np.arange(n), largest] = np.sqrt(np.maximum(0.0, 1.0 - sumsq))
    else:
        xyz = buf["rotations"].reshape(n, 3).astype(np.float32) / 127.5 - 1.0
        w = np.sqrt(np.maximum(0.0, 1.0 - np.sum(xyz * xyz, axis=1)))
        xyzw = np.concatenate([xyz, w[:, None]], axis=1).astype(np.float32)
    rotations = xyzw[:, [3, 0, 1, 2]]
    rotations = rotations / np.linalg.norm(rotations, axis=1, keepdims=True)  # 量子化で単位長からずれる分を補正

    sh = np.zeros((n, 0, 3), dtype=np.float32)
    if shdim:
        sh = ((buf["sh"].reshape(n, shdim, 3).astype(np.float32)) - 128.0) / 128.0
    return Cloud(positions, scales, rotations.astype(np.float32), alphas,
                 colors.astype(np.float32), sh)


def _read_ngsp_v4(data: bytes) -> tuple[Cloud, dict]:
    try:
        import zstandard
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("SPZ v4 の読み込みには `pip install zstandard` が必要です") from e
    magic, version, n, sh_degree, frac_bits, flags, nstreams, toc_off = struct.unpack_from("<IIIBBBBI", data, 0)
    ext_flag = bool(flags & 2)
    if ext_flag:
        warnings.warn("SPZ拡張(extensions)を含みます。座標系拡張などは解釈していません", stacklevel=2)
    toc = [struct.unpack_from("<QQ", data, toc_off + 16 * i) for i in range(nstreams)]
    off = toc_off + 16 * nstreams
    shdim = SH_DIM[sh_degree]
    rot_bytes = 4 if version >= 3 else 3
    expected = [("positions", n * 9), ("alphas", n), ("colors", n * 3), ("scales", n * 3),
                ("rotations", n * rot_bytes)]
    if shdim:
        expected.append(("sh", n * shdim * 3))
    if len(expected) != nstreams:
        raise ValueError(f"ストリーム数が想定と違います: {nstreams} != {len(expected)}")
    dctx = zstandard.ZstdDecompressor()
    buf = {}
    for (name, size), (csize, usize) in zip(expected, toc):
        if usize != size:
            raise ValueError(f"{name}ストリームのサイズが不正: {usize} != {size}")
        buf[name] = np.frombuffer(dctx.decompress(data[off:off + csize], max_output_size=usize), dtype=np.uint8)
        off += csize
    cloud = _unpack_streams(buf, n, sh_degree, frac_bits, version)
    cloud.antialiased = bool(flags & 1)
    return cloud, dict(version=version, num_points=n, sh_degree=sh_degree, fractional_bits=frac_bits,
                       flags=flags, container="zstd-streams")


def read_spz(path: str) -> Cloud:
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] == b"\x1f\x8b":
        data = gzip.decompress(raw)
        magic, version, n, sh_degree, frac_bits, flags, _res = struct.unpack_from("<IIIBBBB", data, 0)
        if magic != NGSP_MAGIC:
            raise ValueError("SPZのマジックが不正")
        if version < 2 or version > 3:
            raise ValueError(f"gzip形式の未対応バージョン: {version}")
        if sh_degree not in SH_DIM:
            raise ValueError(f"未対応のSH次数: {sh_degree}")
        shdim = SH_DIM[sh_degree]
        rot_bytes = 4 if version >= 3 else 3
        sizes = [("positions", n * 9), ("alphas", n), ("colors", n * 3), ("scales", n * 3),
                 ("rotations", n * rot_bytes), ("sh", n * shdim * 3)]
        off = 16
        buf = {}
        for name, size in sizes:
            if off + size > len(data):
                raise ValueError(f"{name}がファイル終端を超えています(破損?)")
            buf[name] = np.frombuffer(data, dtype=np.uint8, count=size, offset=off)
            off += size
        if flags & 2:
            warnings.warn("SPZ拡張(extensions)を含みます。座標系拡張などは解釈していません", stacklevel=2)
        cloud = _unpack_streams(buf, n, sh_degree, frac_bits, version)
        cloud.antialiased = bool(flags & 1)
        cloud.meta = dict(version=version, num_points=n, sh_degree=sh_degree, fractional_bits=frac_bits,
                          flags=flags, container="gzip")
        return cloud
    if struct.unpack_from("<I", raw, 0)[0] == NGSP_MAGIC:
        cloud, meta = _read_ngsp_v4(raw)
        cloud.meta = meta
        return cloud
    raise ValueError("SPZとして認識できません")


# ----------------------------------------------------------------------------
# SPZ 書き出し(v2/v3, gzip)。往復テストと、PLY->SPZ用。
# ----------------------------------------------------------------------------
def _to_u8(x: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(x), 0, 255).astype(np.uint8)


def write_spz(cloud: Cloud, path: str, version: int = 3, sh1_bits: int = DEFAULT_SH1_BITS,
              sh_rest_bits: int = DEFAULT_SH_REST_BITS) -> None:
    if version not in (2, 3):
        raise ValueError("書き出しは v2/v3 のみ")
    c = convert_coordinates(cloud, "RUB")
    n = c.n
    deg = c.sh_degree
    frac_bits = 12
    fixed = np.clip(np.rint(c.positions * (1 << frac_bits)), -(1 << 23), (1 << 23) - 1).astype(np.int32)
    pos = np.stack([fixed & 0xFF, (fixed >> 8) & 0xFF, (fixed >> 16) & 0xFF], axis=-1).astype(np.uint8)

    alpha = _to_u8(255.0 / (1.0 + np.exp(-c.alphas.astype(np.float64))))
    colors = _to_u8(c.colors * (COLOR_SCALE * 255.0) + 127.5)
    scales = _to_u8((c.scales + 10.0) * 16.0)

    q = c.rotations[:, [1, 2, 3, 0]].astype(np.float64)  # xyzw
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    if version >= 3:
        largest = np.argmax(np.abs(q), axis=1)
        sign_neg = q[np.arange(n), largest] < 0
        comp = largest.astype(np.uint32)
        for i in range(4):
            keep = largest != i
            neg = ((q[:, i] < 0) ^ sign_neg).astype(np.uint32)
            mag = np.floor(511.0 * (np.abs(q[:, i]) / float(SQRT1_2)) + 0.5).astype(np.uint32)
            piece = (neg << 9) | np.minimum(mag, 511)
            comp = np.where(keep, (comp << 10) | piece, comp)
        rot = np.stack([(comp >> s) & 0xFF for s in (0, 8, 16, 24)], axis=-1).astype(np.uint8)
    else:
        q = np.where((q[:, 3] < 0)[:, None], -q, q)
        rot = _to_u8(q[:, :3] * 127.5 + 127.5)

    sh_bytes = b""
    if deg:
        sh = c.sh.astype(np.float64)
        bits = np.where(np.arange(sh.shape[1]) < 3, sh1_bits, sh_rest_bits)
        bucket = (1 << (8 - bits)).astype(np.int32)[None, :, None]
        qv = np.rint(sh * 128.0).astype(np.int32) + 128
        qv = (qv + bucket // 2) // bucket * bucket
        sh_bytes = np.clip(qv, 0, 255).astype(np.uint8).tobytes()

    flags = 1 if c.antialiased else 0
    header = struct.pack("<IIIBBBB", NGSP_MAGIC, version, n, deg, frac_bits, flags, 0)
    payload = header + pos.tobytes() + alpha.tobytes() + colors.tobytes() + scales.tobytes() \
        + rot.tobytes() + sh_bytes
    with open(path, "wb") as f:
        f.write(gzip.compress(payload, compresslevel=9))


# ----------------------------------------------------------------------------
# PLY
# ----------------------------------------------------------------------------
def write_ply(cloud: Cloud, path: str) -> None:
    """INRIA形式の3DGS PLY(binary little endian)を書く。f_restはチャンネル優先(R全部→G全部→B全部)。"""
    n = cloud.n
    k = cloud.sh.shape[1]
    names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"]
    names += [f"f_rest_{i}" for i in range(3 * k)]
    names += ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    cols = [cloud.positions, np.zeros((n, 3), np.float32), cloud.colors]
    if k:
        cols.append(cloud.sh.transpose(0, 2, 1).reshape(n, 3 * k))
    cols += [cloud.alphas[:, None], cloud.scales, cloud.rotations]
    arr = np.ascontiguousarray(np.concatenate(cols, axis=1).astype("<f4"))
    assert arr.shape[1] == len(names)
    header = "ply\nformat binary_little_endian 1.0\n"
    header += f"comment coordinate_system {cloud.coord}\n"
    header += f"element vertex {n}\n" + "".join(f"property float {nm}\n" for nm in names) + "end_header\n"
    with open(path, "wb") as f:
        f.write(header.encode("ascii"))
        f.write(arr.tobytes())


def read_ply(path: str, coord: str = "RDF") -> Cloud:
    with open(path, "rb") as f:
        raw = f.read()
    end = raw.index(b"end_header\n") + len(b"end_header\n")
    lines = raw[:end].decode("ascii").splitlines()
    if "format binary_little_endian 1.0" not in lines:
        raise ValueError("binary_little_endian のPLYのみ対応")
    n = 0
    names = []
    for ln in lines:
        if ln.startswith("element vertex"):
            n = int(ln.split()[-1])
        elif ln.startswith("property"):
            _, typ, nm = ln.split()
            if typ not in ("float", "float32"):
                raise ValueError(f"float以外のプロパティ未対応: {ln}")
            names.append(nm)
        elif ln.startswith("comment coordinate_system"):
            coord = ln.split()[-1]
    arr = np.frombuffer(raw, dtype="<f4", count=n * len(names), offset=end).reshape(n, len(names))
    idx = {nm: i for i, nm in enumerate(names)}
    col = lambda *ns: np.stack([arr[:, idx[x]] for x in ns], axis=1).astype(np.float32)  # noqa: E731
    n_rest = len([x for x in names if x.startswith("f_rest_")])
    if n_rest % 3:
        raise ValueError("f_rest の数が3の倍数ではありません")
    k = n_rest // 3
    if k not in SH_DIM.values():
        raise ValueError(f"f_rest の数が不正: {n_rest}")
    sh = np.zeros((n, 0, 3), np.float32)
    if k:
        sh = col(*[f"f_rest_{i}" for i in range(n_rest)]).reshape(n, 3, k).transpose(0, 2, 1).copy()
    return Cloud(col("x", "y", "z"), col("scale_0", "scale_1", "scale_2"),
                 col("rot_0", "rot_1", "rot_2", "rot_3"), arr[:, idx["opacity"]].astype(np.float32),
                 col("f_dc_0", "f_dc_1", "f_dc_2"), sh, coord.upper())


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _info(cloud: Cloud) -> str:
    p = cloud.positions
    s = np.exp(cloud.scales)
    a = 1 / (1 + np.exp(-cloud.alphas))
    return (f"points={cloud.n} sh_degree={cloud.sh_degree} coord={cloud.coord} meta={cloud.meta}\n"
            f"  bbox min={np.round(p.min(0), 3)} max={np.round(p.max(0), 3)}\n"
            f"  scale median={np.median(s):.4f} p99={np.percentile(s, 99):.4f}  "
            f"alpha mean={a.mean():.3f}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("spz2ply")
    a.add_argument("src")
    a.add_argument("dst")
    a.add_argument("--to", default="RDF", help="出力PLYの座標系(既定RDF=3DGS標準)")
    b = sub.add_parser("ply2spz")
    b.add_argument("src")
    b.add_argument("dst")
    b.add_argument("--from", dest="src_coord", default="RDF")
    b.add_argument("--version", type=int, default=3)
    c = sub.add_parser("info")
    c.add_argument("src")
    args = ap.parse_args(argv)
    if args.cmd == "spz2ply":
        cl = read_spz(args.src)
        print(_info(cl))
        write_ply(convert_coordinates(cl, args.to), args.dst)
    elif args.cmd == "ply2spz":
        cl = read_ply(args.src, args.src_coord)
        write_spz(cl, args.dst, version=args.version)
    else:
        print(_info(read_spz(args.src)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
