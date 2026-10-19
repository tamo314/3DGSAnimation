"""spzply.py のマイルストーンテスト(往復変換・座標系・実サンプル)。

  python scripts/gaussian/test_spzply.py [hornedlizard.spz のパス]

実サンプル(公開SPZ)が無い場合はそのチェックだけスキップする。
"""
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import spzply as sp  # noqa: E402

C0, C1 = 0.28209479177387814, 0.4886025119029199
C2 = [1.0925484305920792, -1.0925484305920792, 0.31539156525252005, -1.0925484305920792, 0.5462742152960396]
C3 = [-0.5900435899266435, 2.890611442640554, -0.4570457994644658, 0.3731763325901154,
      -0.4570457994644658, 1.445305721320277, -0.5900435899266435]


def eval_sh_rgb(dc, sh, d):
    """3DGSと同じSH評価(視線方向dは単位ベクトル)。dc:(3,), sh:(K,3)"""
    x, y, z = d
    res = C0 * dc
    k = len(sh)
    if k >= 3:
        res = res - C1 * y * sh[0] + C1 * z * sh[1] - C1 * x * sh[2]
    if k >= 8:
        xx, yy, zz, xy, yz, xz = x * x, y * y, z * z, x * y, y * z, x * z
        res = (res + C2[0] * xy * sh[3] + C2[1] * yz * sh[4] + C2[2] * (2 * zz - xx - yy) * sh[5]
               + C2[3] * xz * sh[6] + C2[4] * (xx - yy) * sh[7])
    if k >= 15:
        res = (res + C3[0] * y * (3 * xx - yy) * sh[8] + C3[1] * xy * z * sh[9]
               + C3[2] * y * (4 * zz - xx - yy) * sh[10] + C3[3] * z * (2 * zz - 3 * xx - 3 * yy) * sh[11]
               + C3[4] * x * (4 * zz - xx - yy) * sh[12] + C3[5] * z * (xx - yy) * sh[13]
               + C3[6] * x * (xx - 3 * yy) * sh[14])
    return res


def quat_to_mat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def cov(scale_log, q):
    r = quat_to_mat(q / np.linalg.norm(q))
    s = np.diag(np.exp(scale_log))
    m = r @ s
    return m @ m.T


def random_cloud(n, sh_degree, seed=0):
    rng = np.random.default_rng(seed)
    k = sp.SH_DIM[sh_degree]
    q = rng.normal(size=(n, 4)).astype(np.float32)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    return sp.Cloud(
        positions=rng.uniform(-8, 8, (n, 3)).astype(np.float32),
        scales=rng.uniform(-6, -1, (n, 3)).astype(np.float32),
        rotations=q,
        alphas=rng.uniform(-3, 4, n).astype(np.float32),
        colors=rng.uniform(-1.5, 1.5, (n, 3)).astype(np.float32),
        sh=rng.uniform(-0.5, 0.5, (n, k, 3)).astype(np.float32),
        coord="RUB",
    )


def test_roundtrip_spz(version, degree):
    src = random_cloud(2000, degree, seed=version * 10 + degree)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.spz")
        sp.write_spz(src, path, version=version)
        dst = sp.read_spz(path)
    assert dst.n == src.n and dst.sh_degree == degree and dst.meta["version"] == version
    assert np.abs(dst.positions - src.positions).max() < 1 / 4096 / 2 + 1e-6
    assert np.abs(dst.scales - src.scales).max() < 1 / 16 / 2 + 1e-5
    assert np.abs(dst.colors - src.colors).max() < 1 / 255 / sp.COLOR_SCALE / 2 + 1e-4
    a0, a1 = 1 / (1 + np.exp(-src.alphas)), 1 / (1 + np.exp(-dst.alphas))
    assert np.abs(a0 - a1).max() < 1 / 255 / 2 + 1e-4
    # 回転は q と -q が同じ回転。内積の絶対値で比較
    dots = np.abs(np.sum(src.rotations * dst.rotations, axis=1))
    if version >= 3:
        assert dots.min() > 0.999, dots.min()
    else:  # v2は w をxyzから復元するため、wが小さい回転は誤差が大きい(v3で解消された既知の弱点)
        assert np.percentile(dots, 5) > 0.99, np.percentile(dots, 5)
    if degree:
        assert np.abs(dst.sh - src.sh).max() < ((1 << (8 - sp.DEFAULT_SH_REST_BITS)) / 2 + 1) / 128


def test_ply_roundtrip(degree):
    src = random_cloud(500, degree, seed=99 + degree)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.ply")
        sp.write_ply(src, path)
        dst = sp.read_ply(path)
    for f in ("positions", "scales", "rotations", "alphas", "colors", "sh"):
        assert np.array_equal(getattr(src, f), getattr(dst, f)), f
    assert dst.coord == "RUB"


def test_coordinate_conversion():
    src = random_cloud(50, 3, seed=5)
    for to in ("RDF", "LUF", "RUF", "LDB", "RDB"):
        f = sp._sign_vector("RUB") * sp._sign_vector(to)
        dst = sp.convert_coordinates(src, to)
        back = sp.convert_coordinates(dst, "RUB")
        assert np.allclose(back.positions, src.positions) and np.allclose(back.sh, src.sh)
        rng = np.random.default_rng(1)
        for i in range(src.n):
            # 位置
            assert np.allclose(dst.positions[i], f * src.positions[i])
            # 共分散(楕円体の形): Σ' = F Σ F^T
            F = np.diag(f)
            assert np.allclose(cov(dst.scales[i], dst.rotations[i]), F @ cov(src.scales[i], src.rotations[i]) @ F.T,
                               atol=1e-6)
            # SH: 視線方向dの見え方が F d で同じ
            d = rng.normal(size=3)
            d /= np.linalg.norm(d)
            c0 = eval_sh_rgb(src.colors[i], src.sh[i], d)
            c1 = eval_sh_rgb(dst.colors[i], dst.sh[i], f * d)
            assert np.allclose(c0, c1, atol=1e-5), (to, i)


def test_real_sample(path):
    cl = sp.read_spz(path)
    assert cl.n > 10000
    for f in ("positions", "scales", "rotations", "alphas", "colors", "sh"):
        assert np.isfinite(getattr(cl, f)).all(), f
    assert np.allclose(np.linalg.norm(cl.rotations, axis=1), 1.0, atol=1e-3)
    s = np.exp(cl.scales)
    assert 1e-5 < np.median(s) < 1.0, np.median(s)
    with tempfile.TemporaryDirectory() as d:
        ply = os.path.join(d, "o.ply")
        sp.write_ply(sp.convert_coordinates(cl, "RDF"), ply)
        back = sp.convert_coordinates(sp.read_ply(ply), "RUB")
        assert np.allclose(back.positions, cl.positions, atol=1e-6)
        assert np.allclose(back.sh, cl.sh, atol=1e-6)
        spz2 = os.path.join(d, "o.spz")
        sp.write_spz(back, spz2)
        again = sp.read_spz(spz2)
        assert np.abs(again.positions - cl.positions).max() < 1 / 4096 + 1e-6
    print(sp._info(cl))
    return cl


if __name__ == "__main__":
    for v in (2, 3):
        for deg in (0, 1, 2, 3):
            test_roundtrip_spz(v, deg)
    print("SPZ往復(v2/v3, SH0-3): OK")
    for deg in (0, 3):
        test_ply_roundtrip(deg)
    print("PLY往復: OK")
    test_coordinate_conversion()
    print("座標系変換(位置・共分散・SH評価の一致): OK")
    sample = sys.argv[1] if len(sys.argv) > 1 else None
    if sample and os.path.exists(sample):
        test_real_sample(sample)
        print("実SPZサンプル: OK")
    else:
        print("実SPZサンプル: スキップ(パス未指定)")
