"""Layered elastic responses in the sense of BISAR.

Vertical circular loads on a stack of isotropic layers over a half-space.
Interfaces are either fully bonded or connected by a shear spring. The spring
is BISAR's reduced compliance ALK (metres): the horizontal slip is
AK * shear stress, with AK = ALK * (1 + nu) / E of the layer above the joint.

Coordinates: x, y in the surface, z positive downward. Stress and strain are
tension-positive. Displacement uz is positive downward.

The kernels come from the Love strain function. On a homogeneous half-space
they reproduce the Boussinesq solution for a uniform circular pressure.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.special import j0, j1


@dataclass(frozen=True)
class Layer:
    young: float  # Pa
    poisson: float
    thickness: float | None = None  # metres; None for the half-space
    alk: float = 0.0  # reduced shear spring compliance at the bottom, m


@dataclass(frozen=True)
class Load:
    pressure: float  # Pa, downward positive
    radius: float  # m
    x: float = 0.0
    y: float = 0.0


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float
    layer: int  # 0-based layer index used when z falls on an interface


def _mu(layer: Layer) -> float:
    return layer.young / (2.0 * (1.0 + layer.poisson))


def _fields_finite(m, zeta, h, nu, mu, coeff):
    """Ur, Uz, Sz, Tr, dUz for one finite layer. coeff is (A, B, C, D)."""
    A, B, C, D = coeff
    e1 = np.exp(-m * zeta)
    e2 = np.exp(-m * (h - zeta))
    phi = (A + B * zeta) * e1 + (C + D * zeta) * e2
    d1 = (B - m * (A + B * zeta)) * e1 + (D + m * (C + D * zeta)) * e2
    k1 = -m * (2.0 * B - m * (A + B * zeta))
    k2 = m * (2.0 * D + m * (C + D * zeta))
    d2 = k1 * e1 + k2 * e2
    d3 = (m * m * B * e1 + k1 * (-m) * e1) + (m * m * D * e2 + k2 * m * e2)
    Ur = (m * d1) / (2.0 * mu)
    lap = d2 - m * m * phi
    Uz = (2.0 * (1.0 - nu) * lap - d2) / (2.0 * mu)
    Sz = (1.0 - nu) * d3 - (2.0 - nu) * m * m * d1
    Tr = -m * ((1.0 - nu) * lap - d2)
    d_lap = d3 - m * m * d1
    dUz = (2.0 * (1.0 - nu) * d_lap - d3) / (2.0 * mu)
    return Ur, Uz, Sz, Tr, dUz


def _fields_half(m, zeta, nu, mu, coeff):
    """Decaying Love solution in the half-space. coeff is (A, B)."""
    A, B = coeff
    e = np.exp(-m * zeta)
    Ur = m * (B - m * (A + B * zeta)) * e / (2.0 * mu)
    K = -A * m + B * (4.0 * nu - 2.0 - m * zeta)
    Uz = m * K * e / (2.0 * mu)
    Sz = m * m * (A * m + B * m * zeta + B * (1.0 - 2.0 * nu)) * e
    Tr = m * m * (A * m + B * m * zeta - 2.0 * B * nu) * e
    dUz = -m * m * e / (2.0 * mu) * (B + K)
    return Ur, Uz, Sz, Tr, dUz


def _locate_zeta(layers: list[Layer], layer_index: int, z: float) -> float:
    depth = 0.0
    for layer in layers[:layer_index]:
        if layer.thickness is None:
            raise ValueError("half-space must be the last layer")
        depth += layer.thickness
    return z - depth


class _System:
    def __init__(self, layers: list[Layer]):
        if not layers or layers[-1].thickness is not None:
            raise ValueError("the last layer must be a half-space (no thickness)")
        if any(layer.thickness is None for layer in layers[:-1]):
            raise ValueError("only the last layer is a half-space")
        if any(layer.thickness is not None and layer.thickness <= 0 for layer in layers):
            raise ValueError("layer thickness must be positive")
        self.layers = layers
        self.n = len(layers)
        self.n_unknown = 4 * (self.n - 1) + 2

    def _pack(self, values: np.ndarray):
        coeffs = []
        for i in range(self.n - 1):
            coeffs.append(values[4 * i : 4 * i + 4])
        coeffs.append(values[-2:])
        return coeffs

    def evaluate(self, m: float, coeffs, layer_index: int, zeta: float):
        layer = self.layers[layer_index]
        if layer_index == self.n - 1:
            return _fields_half(m, zeta, layer.poisson, _mu(layer), coeffs[layer_index])
        return _fields_finite(
            m, zeta, layer.thickness, layer.poisson, _mu(layer), coeffs[layer_index]
        )

    def solve(self, m: float, pressure: float, radius: float) -> list:
        """Love coefficients for one Hankel wave number and one vertical load."""
        n = self.n
        nu = self.n_unknown
        mat = np.zeros((nu, nu))
        rhs = np.zeros(nu)

        def column(layer_index: int, local: int, zeta: float):
            coeffs = []
            for i in range(n - 1):
                coeffs.append(np.zeros(4))
            coeffs.append(np.zeros(2))
            coeffs[layer_index][local] = 1.0
            return self.evaluate(m, coeffs, layer_index, zeta)

        # Surface traction. Sigma_z Hankel coefficient, tension positive.
        # J1(x)/x -> 1/2 keeps the m = 0 limit finite: Sigma -> -p a^2 / 2.
        ma = m * radius
        if ma < 1e-8:
            load_hat = -pressure * radius * radius / 2.0
        else:
            load_hat = -pressure * radius * float(j1(ma)) / m

        # rows 0, 1: Sz, Tr on the surface of layer 0
        for i_layer, local in self._unknowns_of(0):
            col = self._unknown_index(i_layer, local)
            Ur, Uz, Sz, Tr, dUz = column(i_layer, local, 0.0)
            mat[0, col] = Sz
            mat[1, col] = Tr
        rhs[0] = load_hat
        rhs[1] = 0.0

        row = 2
        for iface in range(n - 1):
            upper = iface
            lower = iface + 1
            h = self.layers[upper].thickness
            alk = self.layers[upper].alk
            # Scale displacements by Young's modulus so they sit near the stresses.
            e_up = self.layers[upper].young
            for i_layer, local in self._unknowns_of(upper):
                col = self._unknown_index(i_layer, local)
                Ur, Uz, Sz, Tr, _ = column(i_layer, local, h)
                mat[row, col] = e_up * Uz
                mat[row + 1, col] = Sz
                mat[row + 2, col] = Tr
                mat[row + 3, col] = e_up * Ur
            for i_layer, local in self._unknowns_of(lower):
                col = self._unknown_index(i_layer, local)
                Ur, Uz, Sz, Tr, _ = column(i_layer, local, 0.0)
                mat[row, col] -= e_up * Uz
                mat[row + 1, col] -= Sz
                mat[row + 2, col] -= Tr
                # ur_above - ur_below + AK * tau = 0, written as
                # E_above*(ur_above - ur_below) + ALK*(1+nu_above)*tau = 0
                mat[row + 3, col] -= e_up * Ur
            if alk != 0.0:
                nu_up = self.layers[upper].poisson
                for i_layer, local in self._unknowns_of(upper):
                    col = self._unknown_index(i_layer, local)
                    _, _, _, Tr, _ = column(i_layer, local, h)
                    mat[row + 3, col] += alk * (1.0 + nu_up) * Tr
            row += 4

        scales = np.max(np.abs(mat), axis=1)
        scales[scales == 0.0] = 1.0
        mat = mat / scales[:, None]
        rhs = rhs / scales
        try:
            values = np.linalg.solve(mat, rhs)
        except np.linalg.LinAlgError:
            values = np.linalg.lstsq(mat, rhs, rcond=None)[0]
        return self._pack(values)

    def _unknowns_of(self, layer_index: int):
        count = 4 if layer_index < self.n - 1 else 2
        return [(layer_index, i) for i in range(count)]

    def _unknown_index(self, layer_index: int, local: int) -> int:
        if layer_index < self.n - 1:
            return 4 * layer_index + local
        return 4 * (self.n - 1) + local


def _quadrature(radius: float, r: float, z: float):
    scale = max(radius, abs(r), 1e-3)
    width = np.pi / scale
    z_eff = max(z, radius * 0.02, 1e-4)
    # Stiff layer contrasts leave a long oscillatory tail, so the upper
    # limit follows both depth and the load radius.
    m_max = max(160.0 / z_eff, 80.0 / scale)
    nseg = int(np.ceil(m_max / width))
    nseg = min(max(nseg, 16), 400)
    xs, ws = leggauss(48)
    mids = (np.arange(nseg) + 0.5) * width
    ms = (mids[:, None] + (0.5 * width) * xs[None, :]).ravel()
    wts = np.broadcast_to(ws * (0.5 * width), (nseg, xs.size)).ravel().copy()
    # drop a singular sample if the node lands on 0
    mask = ms > 1e-10
    return ms[mask], wts[mask]


def _empty_response():
    return {k: 0.0 for k in ("ur", "uz", "sr", "st", "sz", "trz", "er", "et", "ez", "erz")}


def _integrate_cylindrical(layers, load, points: list[Point]) -> list[dict]:
    """One load, many positions. The Hankel system is solved once per wave number."""
    system = _System(layers)
    rs, zs = [], []
    located = []
    for point in points:
        r = float(np.hypot(point.x - load.x, point.y - load.y))
        zeta = _locate_zeta(layers, point.layer, point.z)
        if zeta < -1e-8:
            raise ValueError("position is above the selected layer")
        rs.append(r)
        zs.append(point.z)
        located.append((point, r, zeta))
    ms, wts = _quadrature(load.radius, max(rs) if rs else 0.0, min(zs) if zs else load.radius)
    spectra = [system.solve(float(m), load.pressure, load.radius) for m in ms]
    out = []
    for point, r, zeta in located:
        acc = {k: 0.0 for k in ("ur", "uz", "sz", "trz", "ez", "ert")}
        for m, w, coeffs in zip(ms, wts, spectra):
            Ur, Uz, Sz, Tr, dUz = system.evaluate(float(m), coeffs, point.layer, float(zeta))
            j0r = 1.0 if r < 1e-12 else float(j0(m * r))
            j1r = 0.0 if r < 1e-12 else float(j1(m * r))
            acc["uz"] += w * Uz * j0r * m
            acc["ur"] += w * Ur * j1r * m
            acc["sz"] += w * Sz * j0r * m
            acc["trz"] += w * Tr * j1r * m
            acc["ez"] += w * dUz * j0r * m
            acc["ert"] += w * (m * Ur) * j0r * m
        layer = layers[point.layer]
        mu = _mu(layer)
        lam = layer.young * layer.poisson / ((1.0 + layer.poisson) * (1.0 - 2.0 * layer.poisson))
        ert = acc["ert"]
        if r < 1e-12:
            et = 0.5 * ert
            er = 0.5 * ert
        else:
            et = acc["ur"] / r
            er = ert - et
        ez = acc["ez"]
        vol = er + et + ez
        out.append(
            {
                "ur": acc["ur"],
                "uz": acc["uz"],
                "sr": lam * vol + 2.0 * mu * er,
                "st": lam * vol + 2.0 * mu * et,
                "sz": acc["sz"],
                "trz": acc["trz"],
                "er": er,
                "et": et,
                "ez": ez,
                "erz": 0.5 * acc["trz"] / mu,
            }
        )
    return out


def response_one_load(layers: list[Layer], load: Load, r: float, z: float, layer_index: int) -> dict:
    """Cylindrical response of a single vertical load whose centre is the origin."""
    point = Point(r, 0.0, z, layer_index)
    return _integrate_cylindrical(layers, load, [point])[0]

    ert = acc["ert"]
    if abs(r) < 1e-12:
        et = 0.5 * ert
        er = 0.5 * ert
    else:
        # εθ = ur / r was accumulated as the displacement; divide.
        et = acc["ur"] / r
        er = ert - et
    ez = acc["ez"]
    vol = er + et + ez
    sr = lam * vol + 2.0 * mu * er
    st = lam * vol + 2.0 * mu * et
    # tensor shear strain
    erz = 0.5 * acc["trz"] / mu
    return {
        "ur": acc["ur"],
        "uz": acc["uz"],
        "sr": sr,
        "st": st,
        "sz": acc["sz"],
        "trz": acc["trz"],
        "er": er,
        "et": et,
        "ez": ez,
        "erz": erz,
    }


def to_cartesian(cyl: dict, theta: float) -> dict:
    """Cylindrical tensor about a load centre -> global x, y, z."""
    c = np.cos(theta)
    s = np.sin(theta)
    sr, st, sz = cyl["sr"], cyl["st"], cyl["sz"]
    tr = cyl["trz"]
    er, et, ez = cyl["er"], cyl["et"], cyl["ez"]
    gr = cyl["erz"]
    ur, uz = cyl["ur"], cyl["uz"]
    return {
        "ux": ur * c,
        "uy": ur * s,
        "uz": uz,
        "sx": sr * c * c + st * s * s,
        "sy": sr * s * s + st * c * c,
        "sz": sz,
        "txy": (sr - st) * s * c,
        "txz": tr * c,
        "tyz": tr * s,
        "ex": er * c * c + et * s * s,
        "ey": er * s * s + et * c * c,
        "ez": ez,
        "exy": (er - et) * s * c,
        "exz": gr * c,
        "eyz": gr * s,
    }


_CART_KEYS = ("ux", "uy", "uz", "sx", "sy", "sz", "txy", "txz", "tyz", "ex", "ey", "ez", "exy", "exz", "eyz")


def analyse(layers: list[Layer], loads: list[Load], points: list[Point]) -> list[dict]:
    """Superpose every load at every position. This is the Calculate action."""
    totals = [{k: 0.0 for k in _CART_KEYS} for _ in points]
    per_loads: list[list] = [[] for _ in points]
    for load in loads:
        cylindrical = _integrate_cylindrical(layers, load, points)
        for point, cyl, total, bucket in zip(points, cylindrical, totals, per_loads):
            dx = point.x - load.x
            dy = point.y - load.y
            r = float(np.hypot(dx, dy))
            theta = float(np.atan2(dy, dx)) if r > 0.0 else 0.0
            cart = to_cartesian(cyl, theta)
            bucket.append({"r": r, "theta": theta, "cylindrical": cyl, "cartesian": cart})
            for key in _CART_KEYS:
                total[key] += cart[key]
    out = []
    for point, total, bucket in zip(points, totals, per_loads):
        total.update(_invariants(total, layers[point.layer]))
        total["per_load"] = bucket
        total["point"] = point
        out.append(total)
    return out


def combine(layers: list[Layer], loads: list[Load], point: Point) -> dict:
    """Superpose every load at one position and add principals and energies."""
    return analyse(layers, loads, [point])[0]


def _invariants(cart: dict, layer: Layer) -> dict:
    stress = np.array(
        [
            [cart["sx"], cart["txy"], cart["txz"]],
            [cart["txy"], cart["sy"], cart["tyz"]],
            [cart["txz"], cart["tyz"], cart["sz"]],
        ]
    )
    strain = np.array(
        [
            [cart["ex"], cart["exy"], cart["exz"]],
            [cart["exy"], cart["ey"], cart["eyz"]],
            [cart["exz"], cart["eyz"], cart["ez"]],
        ]
    )
    ss, sv = np.linalg.eigh(stress)
    es, ev = np.linalg.eigh(strain)
    # eigh is ascending: minimum, minimax, maximum
    order = (2, 1, 0)
    normals = []
    for i in order:
        vec = sv[:, i].copy()
        pivot = int(np.argmax(np.abs(vec)))
        if vec[pivot] < 0:
            vec = -vec
        normals.append(
            {
                "stress": float(ss[i]),
                "strain": float(es[i]),
                "direction": vec,
            }
        )
    energy = 0.5 * float(np.tensordot(stress, strain))
    sm = np.trace(stress) / 3.0
    em = np.trace(strain) / 3.0
    distort = 0.5 * float(np.tensordot(stress - sm * np.eye(3), strain - em * np.eye(3)))
    pairs = ((0, 2), (1, 2), (0, 1))  # max-min, mid-min, max-mid in descending list
    shears = []
    for i, j in pairs:
        ni = normals[i]["direction"]
        nj = normals[j]["direction"]
        bisector = (ni - nj) / np.sqrt(2.0)
        midline = (ni + nj) / np.sqrt(2.0)
        bp = int(np.argmax(np.abs(bisector)))
        if bisector[bp] < 0:
            bisector = -bisector
            midline = -midline
        shears.append(
            {
                "stress": 0.5 * (normals[i]["stress"] - normals[j]["stress"]),
                "strain": 0.5 * (normals[i]["strain"] - normals[j]["strain"]),
                "direction": bisector,
                "midpoint": 0.5 * (normals[i]["stress"] + normals[j]["stress"]),
                "mid_direction": midline,
            }
        )
    return {
        "principals": normals,
        "shears": shears,
        "strain_energy": energy,
        "distortion_energy": distort,
        "young": layer.young,
        "poisson": layer.poisson,
    }
