"""Bonded multi-layer elastic response under circular vertical loads.

The Hankel solution follows the Love function used for layered pavements:
each layer has four coefficients, the half-space has two, and full bond makes
displacement and traction continuous at the interfaces. On the load axis the
inverse transforms reduce to ordinary integrals, which are summed between the
zeros of the Bessel factor that comes from the circular load.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import j1, jn_zeros

from bisar.model import Components, Layer, Load, PointResult, Problem, QueryPoint

_BESSEL_ZEROS = jn_zeros(1, 240)
_GAUSS_NODES, _GAUSS_WEIGHTS = np.polynomial.legendre.leggauss(24)


def solve(problem: Problem) -> tuple[PointResult, ...]:
    if any(layer.shear_spring != 0.0 for layer in problem.layers):
        raise NotImplementedError("Interface slip is not implemented yet.")
    if any(load.shear_stress != 0.0 for load in problem.loads):
        raise NotImplementedError("Horizontal shear loads are not implemented yet.")
    if any(_offset(point, load) > 1e-9 for point in problem.points for load in problem.loads):
        raise NotImplementedError("Positions off the load axis are not implemented yet.")

    totals = np.zeros((len(problem.points), 3))
    for load in problem.loads:
        totals += _axis_responses(problem.layers, load, problem.points)

    results = []
    for point, (vertical_disp, vertical_stress, radial_stress) in zip(problem.points, totals):
        layer = problem.layers[point.layer - 1]
        strain_z, strain_r = _hooke(layer, vertical_stress, radial_stress)
        results.append(
            PointResult(
                position=point.number,
                layer=point.layer,
                x=point.x,
                y=point.y,
                z=point.z,
                displacement=Components(0.0, 0.0, float(vertical_disp)),
                stress=Components(float(radial_stress), float(radial_stress), float(vertical_stress)),
                strain=Components(float(strain_r), float(strain_r), float(strain_z)),
            )
        )
    return tuple(results)


def _offset(point: QueryPoint, load: Load) -> float:
    return math.hypot(point.x - load.x, point.y - load.y)


def _hooke(layer: Layer, stress_z: float, stress_r: float) -> tuple[float, float]:
    strain_z = (stress_z - 2.0 * layer.poisson * stress_r) / layer.modulus
    strain_r = ((1.0 - layer.poisson) * stress_r - layer.poisson * stress_z) / layer.modulus
    return strain_z, strain_r


def _axis_responses(layers: tuple[Layer, ...], load: Load, points: tuple[QueryPoint, ...]) -> np.ndarray:
    """Return uz, sz, sr on the load axis for one circular pressure.

    The integrand is the multilayer kernel minus the half-space kernel of the
    surface material. Their difference decays once the wavelength is shorter
    than the top layer, and the half-space part is added from its closed form.
    """
    stack = _Stack(layers)
    surface = layers[0]
    half = _Stack((Layer(surface.modulus, surface.poisson, 0.0, 0.0),))
    locations = [stack.locate(point.z) for point in points]
    half_locations = [(0, point.z) for point in points]
    acc = np.array(
        [
            _halfspace_closed(point.z, load.stress, load.radius, surface.modulus, surface.poisson)
            for point in points
        ]
    )
    if len(layers) == 1:
        return acc
    limit = 40.0 / float(min(layer.thickness for layer in layers[:-1]))
    edges = np.concatenate(([0.0], _BESSEL_ZEROS / load.radius))
    for i in range(len(edges) - 1):
        if edges[i] >= limit:
            break
        hi = min(edges[i + 1], limit)
        acc += _segment(stack, half, load, locations, half_locations, edges[i], hi)
    return acc


def _halfspace_closed(depth: float, pressure: float, radius: float, modulus: float, poisson: float) -> np.ndarray:
    """Centerline response of one homogeneous half-space. Compression is negative."""
    reach = math.sqrt(radius * radius + depth * depth)
    vertical = -pressure * (1.0 - depth**3 / reach**3)
    radial = -(pressure / 2.0) * (
        (1.0 + 2.0 * poisson) - 2.0 * (1.0 + poisson) * depth / reach + depth**3 / reach**3
    )
    settlement = (1.0 + poisson) * pressure / modulus * (
        radius * radius / reach + (1.0 - 2.0 * poisson) * (reach - depth)
    )
    return np.array([settlement, vertical, radial])


def _segment(
    stack: _Stack,
    reference: _Stack,
    load: Load,
    locations: list[tuple[int, float]],
    reference_locations: list[tuple[int, float]],
    lo: float,
    hi: float,
) -> np.ndarray:
    mid = 0.5 * (lo + hi)
    span = 0.5 * (hi - lo)
    samples = mid + span * _GAUSS_NODES
    total = np.zeros((len(locations), 3))
    for xi, weight in zip(samples, _GAUSS_WEIGHTS):
        xi = float(xi)
        if xi < 1e-10:
            continue
        values = stack.axis_fields(xi, load.stress, load.radius, locations)
        values -= reference.axis_fields(xi, load.stress, load.radius, reference_locations)
        total += (span * weight) * xi * values
    return total


class _Stack:
    def __init__(self, layers: tuple[Layer, ...]) -> None:
        self.moduli = np.array([layer.modulus for layer in layers], dtype=float)
        self.nu = np.array([layer.poisson for layer in layers], dtype=float)
        self.mu = self.moduli / (2.0 * (1.0 + self.nu))
        thicknesses = [layer.thickness for layer in layers[:-1]]
        if any(h <= 0.0 for h in thicknesses):
            raise ValueError("Only the bottom layer may have zero thickness.")
        self.h = np.array(thicknesses, dtype=float)
        self.n = len(layers)
        self.unknowns = 4 * (self.n - 1) + 2

    def locate(self, depth: float) -> tuple[int, float]:
        top = 0.0
        for index, thickness in enumerate(self.h):
            if depth <= top + thickness + 1e-12:
                return index, max(0.0, depth - top)
            top += thickness
        return self.n - 1, max(0.0, depth - top)

    def axis_fields(self, xi: float, pressure: float, radius: float, locations: list[tuple[int, float]]) -> np.ndarray:
        coeffs = self._coefficients(xi, pressure, radius)
        out = np.zeros((len(locations), 3))
        for row, (layer, local_z) in enumerate(locations):
            uz, sz, h2 = _fields(
                xi,
                local_z,
                None if layer == self.n - 1 else float(self.h[layer]),
                float(self.nu[layer]),
                float(self.mu[layer]),
                coeffs[layer],
            )
            out[row, 0] = uz
            out[row, 1] = sz
            out[row, 2] = 0.5 * h2
        return out

    def _coefficients(self, xi: float, pressure: float, radius: float) -> list[np.ndarray]:
        argument = xi * radius
        if argument < 1e-8:
            load = pressure * radius * radius * 0.5
        else:
            load = pressure * radius * j1(argument) / xi
        matrix = np.zeros((self.unknowns, self.unknowns))
        rhs = np.zeros(self.unknowns)
        self._put(matrix, 0, xi, 0, 0.0, "sz")
        rhs[0] = -load
        self._put(matrix, 1, xi, 0, 0.0, "trz")
        row = 2
        scale = float(self.mu[0]) * xi
        for layer in range(self.n - 1):
            for component in ("ur", "uz", "sz", "trz"):
                factor = scale if component in ("ur", "uz") else 1.0
                self._put(matrix, row, xi, layer, float(self.h[layer]), component, factor)
                self._put(matrix, row, xi, layer + 1, 0.0, component, -factor)
                row += 1
        solved = np.linalg.solve(matrix, rhs)
        coeffs = []
        for layer in range(self.n - 1):
            coeffs.append(solved[4 * layer : 4 * layer + 4])
        coeffs.append(np.array([solved[-2], solved[-1], 0.0, 0.0]))
        return coeffs

    def _put(
        self,
        matrix: np.ndarray,
        row: int,
        xi: float,
        layer: int,
        local_z: float,
        component: str,
        factor: float = 1.0,
    ) -> None:
        infinite = layer == self.n - 1
        thickness = None if infinite else float(self.h[layer])
        weights = _weights(
            component,
            xi,
            local_z,
            float(self.nu[layer]),
            float(self.mu[layer]),
            *_decay(xi, local_z, thickness),
        )
        start = 4 * layer if not infinite else 4 * (self.n - 1)
        width = 2 if infinite else 4
        matrix[row, start : start + width] += factor * weights[:width]


def _fields(xi: float, local_z: float, thickness: float | None, nu: float, mu: float, coeff: np.ndarray) -> tuple[float, float, float]:
    weights_z = _weights("uz", xi, local_z, nu, mu, *_decay(xi, local_z, thickness))
    weights_s = _weights("sz", xi, local_z, nu, mu, *_decay(xi, local_z, thickness))
    weights_h = _weights("H2", xi, local_z, nu, mu, *_decay(xi, local_z, thickness))
    return (
        float(np.dot(weights_z, coeff)),
        float(np.dot(weights_s, coeff)),
        float(np.dot(weights_h, coeff)),
    )


def _decay(xi: float, local_z: float, thickness: float | None) -> tuple[float, float]:
    em = math.exp(-xi * local_z)
    if thickness is None:
        return em, 0.0
    return em, math.exp(-xi * max(thickness - local_z, 0.0))


def _weights(component: str, xi: float, local_z: float, nu: float, mu: float, em: float, ep: float) -> np.ndarray:
    depth = xi * local_z
    if component == "uz":
        return np.array(
            [-em, (-2.0 + 4.0 * nu - depth) * em, -ep, (2.0 - 4.0 * nu - depth) * ep]
        )
    if component == "ur":
        return np.array([-em, (1.0 - depth) * em, ep, (1.0 + depth) * ep])
    stress = 2.0 * mu * xi
    if component == "sz":
        return stress * np.array([em, (1.0 - 2.0 * nu + depth) * em, -ep, (1.0 - 2.0 * nu - depth) * ep])
    if component == "trz":
        return stress * np.array([em, (-2.0 * nu + depth) * em, ep, (2.0 * nu + depth) * ep])
    if component == "H2":
        return stress * np.array([-em, (1.0 + 4.0 * nu - depth) * em, ep, (1.0 + 4.0 * nu + depth) * ep])
    raise ValueError(component)
