"""T9: メッシュ頂点の簡単な変形(骨の代わりの手続き的なスキニング)。ガウシアン層とBlender側の元メッシュに同じ関数を適用して比べる。
座標は Blender世界(足元原点、前方-Y、Z上、キャラの左右はX)。numpy配列(N,3)を受け取り、変形後を返す。
"""
import numpy as np


def _smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def lean(V, deg=20.0, pivot_z=0.45, top_z=0.75):
    """上半身を前に倒す(腰の高さを支点)。重みは高さで滑らかに0→1。"""
    V = np.asarray(V, dtype=np.float64)
    w = _smoothstep(V[:, 2], pivot_z, top_z)[:, None]
    p = np.array([0.0, 0.0, pivot_z])
    Vr = (V - p) @ _rot("x", -deg).T + p            # 前(-Y)へ倒れる向き
    return V * (1 - w) + Vr * w


def raise_arm(V, side=+1, deg=55.0, shoulder=(0.11, 0.0, 0.93), hand=(0.27, 0.0, 0.52), radius=(0.06, 0.10)):
    """片腕を肩の前後軸(Y)まわりに持ち上げる(Aポーズの腕を横に開く)。腕の骨(肩→手の線分)からの距離で重みをつける。"""
    V = np.asarray(V, dtype=np.float64)
    S = np.array([side * shoulder[0], shoulder[1], shoulder[2]])
    H = np.array([side * hand[0], hand[1], hand[2]])
    d = H - S
    t = ((V - S) @ d) / (d @ d)
    proj = S + np.clip(t, 0, 1)[:, None] * d
    r = np.linalg.norm(V - proj, axis=1)
    w = _smoothstep(t, 0.05, 0.35) * (1 - _smoothstep(r, radius[0], radius[1]))
    w = w[:, None]
    ang = -deg * side                                # 外側へ持ち上げる向き
    Vr = (V - S) @ _rot("y", ang).T + S
    return V * (1 - w) + Vr * w


def turn_head(V, deg=40.0, neck_z=0.97, blend=0.06, head_z=1.0):
    """頭を縦軸まわりに回す(首の高さを境に滑らかに)。支点は頭部の重心のXY。"""
    V = np.asarray(V, dtype=np.float64)
    head = V[V[:, 2] > head_z]
    pivot = np.array([head[:, 0].mean(), head[:, 1].mean(), neck_z])
    w = _smoothstep(V[:, 2], neck_z, neck_z + blend)[:, None]
    Vr = (V - pivot) @ _rot("z", deg).T + pivot
    return V * (1 - w) + Vr * w


def pose(V, name):
    if name == "rest":
        return np.asarray(V, dtype=np.float64)
    if name == "lean":
        return lean(V, 20.0)
    if name == "arm_r":
        return raise_arm(V, +1, 55.0)
    if name == "arm_l":
        return raise_arm(V, -1, 55.0)
    if name == "head":
        return turn_head(V, 40.0)
    if name == "wave":
        return turn_head(lean(raise_arm(raise_arm(V, +1, 70.0), -1, 25.0), 10.0), 30.0)
    raise ValueError(name)
