"""Bonded multi-layer elastic response under circular vertical and shear loads.

The Hankel solution follows the Love function used for layered pavements:
each layer has four coefficients, the half-space has two, and full bond makes
displacement and traction continuous at the interfaces. On the load axis the
inverse transforms reduce to ordinary integrals, which are summed between the
zeros of the Bessel factor that comes from the circular load.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.special import j0, j1, jn, jn_zeros

from bisar.model import Components, Layer, Load, PointResult, Problem, QueryPoint, Tensor, Vector3

_BESSEL_ZEROS = jn_zeros(1, 240)
_GAUSS_NODES, _GAUSS_WEIGHTS = np.polynomial.legendre.leggauss(24)
_SHEAR_NODES, _SHEAR_WEIGHTS = np.polynomial.legendre.leggauss(48)


def solve(problem: Problem) -> tuple[PointResult, ...]:
    count = len(problem.points)
    displacement = np.zeros((count, 3))
    stress = np.zeros((count, 6))
    for load in problem.loads:
        on_axis = [index for index, point in enumerate(problem.points) if _offset(point, load) <= 1e-9]
        off_axis = [index for index, point in enumerate(problem.points) if index not in on_axis]
        if on_axis:
            subset = tuple(problem.points[index] for index in on_axis)
            for slot, values in zip(on_axis, _axis_responses(problem.layers, load, subset)):
                vertical_disp, vertical_stress, radial_stress = values
                displacement[slot, 2] += vertical_disp
                stress[slot, 0] += radial_stress
                stress[slot, 1] += radial_stress
                stress[slot, 2] += vertical_stress
        if off_axis:
            subset = tuple(problem.points[index] for index in off_axis)
            for slot, point, values in zip(off_axis, subset, _off_axis_responses(problem.layers, load, subset)):
                _add_cylindrical(displacement[slot], stress[slot], point, load, values)
        if load.shear_stress != 0.0:
            _add_horizontal(displacement, stress, problem.layers, load, problem.points)

    results = []
    for point, disp, comp in zip(problem.points, displacement, stress):
        layer = problem.layers[point.layer - 1]
        strain = _hooke_cartesian(layer, comp)
        results.append(
            PointResult(
                position=point.number,
                layer=point.layer,
                x=point.x,
                y=point.y,
                z=point.z,
                displacement=Components(float(disp[0]), float(disp[1]), float(disp[2])),
                stress=Components(float(comp[0]), float(comp[1]), float(comp[2])),
                strain=Components(float(strain[0]), float(strain[1]), float(strain[2])),
                total_displacement=Vector3(float(disp[0]), float(disp[1]), float(disp[2])),
                total_stress=Tensor(*[float(item) for item in comp]),
                total_strain=Tensor(*[float(item) for item in strain]),
            )
        )
    return tuple(results)


def _offset(point: QueryPoint, load: Load) -> float:
    return math.hypot(point.x - load.x, point.y - load.y)


def _hooke_cartesian(layer: Layer, stress: np.ndarray) -> np.ndarray:
    xx, yy, zz, yz, xz, xy = (float(item) for item in stress)
    modulus = layer.modulus
    poisson = layer.poisson
    shear = (1.0 + poisson) / modulus
    return np.array(
        [
            (xx - poisson * (yy + zz)) / modulus,
            (yy - poisson * (xx + zz)) / modulus,
            (zz - poisson * (xx + yy)) / modulus,
            shear * yz,
            shear * xz,
            shear * xy,
        ]
    )


def _add_cylindrical(
    displacement: np.ndarray,
    stress: np.ndarray,
    point: QueryPoint,
    load: Load,
    values: np.ndarray,
) -> None:
    """Rotate one load's cylindrical response into the fixed X-Y frame and add it."""
    radial_disp, vertical_disp, radial_stress, tangential_stress, vertical_stress, shear = values
    angle = math.atan2(point.y - load.y, point.x - load.x)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    displacement[0] += radial_disp * cosine
    displacement[1] += radial_disp * sine
    displacement[2] += vertical_disp
    stress[0] += radial_stress * cosine * cosine + tangential_stress * sine * sine
    stress[1] += radial_stress * sine * sine + tangential_stress * cosine * cosine
    stress[2] += vertical_stress
    stress[3] += shear * sine
    stress[4] += shear * cosine
    stress[5] += (radial_stress - tangential_stress) * sine * cosine


def _axis_responses(layers: tuple[Layer, ...], load: Load, points: tuple[QueryPoint, ...]) -> np.ndarray:
    """Return uz, sz, sr on the load axis for one circular pressure.

    The integrand is the multilayer kernel minus the half-space kernel of the
    surface material. Their difference decays once the wavelength is shorter
    than the top layer, and the half-space part is added from its closed form.
    """
    stack = _Stack(layers)
    surface = layers[0]
    half = _Stack((Layer(surface.modulus, surface.poisson, 0.0, 0.0),))
    locations = [stack.location(point.layer, point.z) for point in points]
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


def _off_axis_responses(layers: tuple[Layer, ...], load: Load, points: tuple[QueryPoint, ...]) -> np.ndarray:
    """Return ur, uz, sr, st, sz, trz for points away from one load axis."""
    stack = _Stack(layers)
    locations = [stack.location(point.layer, point.z) for point in points]
    radii = np.array([_offset(point, load) for point in points])
    mus = np.array([float(stack.mu[layer]) for layer, _local_z in locations])
    depth = min(max(point.z, 0.0) for point in points)
    limit = 40.0 / max(depth, 1e-3)
    scale = max(load.radius, float(np.max(radii)))
    edges = np.concatenate(([0.0], _BESSEL_ZEROS / scale))
    acc = np.zeros((len(points), 6))
    for index in range(len(edges) - 1):
        if edges[index] >= limit:
            break
        hi = min(float(edges[index + 1]), limit)
        acc += _off_segment(stack, load, locations, radii, float(edges[index]), hi)
    radial = 0.5 * acc[:, 4] - mus * acc[:, 5]
    tangential = 0.5 * acc[:, 4] + mus * acc[:, 5]
    return np.column_stack([acc[:, 1], acc[:, 0], radial, tangential, acc[:, 2], acc[:, 3]])


def _off_segment(
    stack: _Stack,
    load: Load,
    locations: list[tuple[int, float]],
    radii: np.ndarray,
    lo: float,
    hi: float,
) -> np.ndarray:
    mid = 0.5 * (lo + hi)
    span = 0.5 * (hi - lo)
    samples = mid + span * _GAUSS_NODES
    total = np.zeros((len(locations), 6))
    for xi, weight in zip(samples, _GAUSS_WEIGHTS):
        xi = float(xi)
        if xi < 1e-10:
            continue
        bars = stack.radial_bars(xi, load.stress, load.radius, locations)
        argument = xi * radii
        circular = j0(argument)
        first = j1(argument)
        second = jn(2, argument)
        factor = (span * weight) * xi
        total[:, 0] += factor * bars[:, 0] * circular
        total[:, 1] += factor * bars[:, 1] * first
        total[:, 2] += factor * bars[:, 2] * circular
        total[:, 3] += factor * bars[:, 3] * first
        total[:, 4] += factor * bars[:, 4] * circular
        total[:, 5] += factor * xi * bars[:, 1] * second
    return total


class _Stack:
    def __init__(self, layers: tuple[Layer, ...]) -> None:
        self.moduli = np.array([layer.modulus for layer in layers], dtype=float)
        self.nu = np.array([layer.poisson for layer in layers], dtype=float)
        self.mu = self.moduli / (2.0 * (1.0 + self.nu))
        self.compliance = np.array([layer.shear_spring for layer in layers], dtype=float)
        thicknesses = [layer.thickness for layer in layers[:-1]]
        if any(h <= 0.0 for h in thicknesses):
            raise ValueError("Only the bottom layer may have zero thickness.")
        self.h = np.array(thicknesses, dtype=float)
        self.n = len(layers)
        self.unknowns = 4 * (self.n - 1) + 2

    def location(self, layer_number: int, depth: float) -> tuple[int, float]:
        index = layer_number - 1
        if not 0 <= index < self.n:
            raise ValueError(f"layer {layer_number} is outside the structure")
        top = float(self.h[:index].sum()) if index else 0.0
        return index, depth - top

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

    def radial_bars(
        self,
        xi: float,
        pressure: float,
        radius: float,
        locations: list[tuple[int, float]],
    ) -> np.ndarray:
        coeffs = self._coefficients(xi, pressure, radius)
        out = np.zeros((len(locations), 5))
        for row, (layer, local_z) in enumerate(locations):
            thickness = None if layer == self.n - 1 else float(self.h[layer])
            nu = float(self.nu[layer])
            mu = float(self.mu[layer])
            coeff = coeffs[layer]
            decay = _decay(xi, local_z, thickness)
            out[row, 0] = np.dot(_weights("uz", xi, local_z, nu, mu, *decay), coeff)
            out[row, 1] = np.dot(_weights("ur", xi, local_z, nu, mu, *decay), coeff)
            out[row, 2] = np.dot(_weights("sz", xi, local_z, nu, mu, *decay), coeff)
            out[row, 3] = np.dot(_weights("trz", xi, local_z, nu, mu, *decay), coeff)
            out[row, 4] = np.dot(_weights("H2", xi, local_z, nu, mu, *decay), coeff)
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
                reduced = float(self.compliance[layer])
                if component == "ur" and reduced != 0.0:
                    # ALK is the reduced compliance in metres. The standard compliance
                    # of the layer above the interface is AK = ALK (1+ν)/E, and the
                    # radial slip is ur_above - ur_below = -AK τ_rz.
                    standard = reduced * (1.0 + float(self.nu[layer])) / float(self.moduli[layer])
                    self._put(matrix, row, xi, layer, float(self.h[layer]), "trz", factor * standard)
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


def _add_horizontal(
    displacement: np.ndarray,
    stress: np.ndarray,
    layers: tuple[Layer, ...],
    load: Load,
    points: tuple[QueryPoint, ...],
) -> None:
    """Add one circular horizontal traction, aimed along ``shear_direction``."""
    direction = math.radians(load.shear_direction)
    cosine = math.cos(direction)
    sine = math.sin(direction)
    depth = min(max(point.z, 0.0) for point in points)
    thicknesses = [layer.thickness for layer in layers[:-1]]
    scale = min([depth, *thicknesses]) if thicknesses else depth
    limit = 40.0 / max(scale, 1e-3)
    edges = np.concatenate(([0.0], _BESSEL_ZEROS / load.radius))
    placed = [_horizontal_place(point, load, cosine, sine) for point in points]
    for index in range(len(edges) - 1):
        if edges[index] >= limit:
            break
        hi = min(float(edges[index + 1]), limit)
        mid = 0.5 * (float(edges[index]) + hi)
        span = 0.5 * (hi - float(edges[index]))
        for node, weight in zip(_SHEAR_NODES, _SHEAR_WEIGHTS):
            xi = float(mid + span * node)
            if xi < 1e-8:
                continue
            solved = _shear_coefficients(xi, layers, load.shear_stress, load.radius)
            factor = span * float(weight) * xi
            for row, point, place in zip(range(len(points)), points, placed):
                layer = layers[point.layer - 1]
                local_z = point.z - _layer_top(layers, point.layer - 1)
                thickness = None if point.layer == len(layers) else layer.thickness
                sample = _shear_sample(
                    xi,
                    local_z,
                    thickness,
                    layer.poisson,
                    _shear_vector(solved, layers, point.layer - 1),
                    place,
                )
                _rotate_horizontal(displacement[row], stress[row], sample, cosine, sine, factor, layer)


def _horizontal_place(point: QueryPoint, load: Load, cosine: float, sine: float) -> tuple[float, float, float]:
    dx = point.x - load.x
    dy = point.y - load.y
    along = dx * cosine + dy * sine
    across = -dx * sine + dy * cosine
    return math.hypot(along, across), along, across


def _layer_top(layers: tuple[Layer, ...], index: int) -> float:
    return sum(layer.thickness for layer in layers[:index])


def _rotate_horizontal(
    displacement: np.ndarray,
    stress: np.ndarray,
    sample: np.ndarray,
    cosine: float,
    sine: float,
    factor: float,
    layer: Layer,
) -> None:
    """Rotate one shear-frame sample into the fixed frame and add it."""
    modulus = layer.modulus
    two_mu = modulus / (1.0 + layer.poisson)
    ux_s = factor * sample[0] / two_mu
    uy_s = factor * sample[1] / two_mu
    uz_s = factor * sample[2] / two_mu
    xx_s = factor * sample[3]
    yy_s = factor * sample[4]
    zz_s = factor * sample[5]
    yz_s = factor * sample[6]
    xz_s = factor * sample[7]
    xy_s = factor * sample[8]
    displacement[0] += ux_s * cosine - uy_s * sine
    displacement[1] += ux_s * sine + uy_s * cosine
    displacement[2] += uz_s
    cc = cosine * cosine
    ss = sine * sine
    sc = sine * cosine
    stress[0] += cc * xx_s + ss * yy_s - 2.0 * sc * xy_s
    stress[1] += ss * xx_s + cc * yy_s + 2.0 * sc * xy_s
    stress[2] += zz_s
    stress[3] += sine * xz_s + cosine * yz_s
    stress[4] += cosine * xz_s - sine * yz_s
    stress[5] += sc * (xx_s - yy_s) + (cc - ss) * xy_s


def _shear_sample(
    xi: float,
    local_z: float,
    thickness: float | None,
    nu: float,
    coeff: tuple[float, ...],
    place: tuple[float, float, float],
) -> np.ndarray:
    """Cartesian ux, uy, uz*2μ and stresses in the frame where the shear points along X."""
    ux0, ux2, uz, t0, t2, sz, lap = _shear_fields(xi, local_z, thickness, nu, coeff)
    radius, along, across = place
    theta = math.atan2(across, along)
    c1, s1 = math.cos(theta), math.sin(theta)
    c2, s2 = math.cos(2.0 * theta), math.sin(2.0 * theta)
    c3, s3 = math.cos(3.0 * theta), math.sin(3.0 * theta)
    if radius < 1e-12:
        b0, b1, b2, b3 = 1.0, 0.0, 0.0, 0.0
    else:
        argument = xi * radius
        b0, b1, b2, b3 = j0(argument), j1(argument), jn(2, argument), jn(3, argument)
    sxx = (nu * lap - xi * ux0 + 0.5 * xi * ux2) * c1 * b1 - 0.5 * xi * ux2 * c3 * b3
    syy = (nu * lap + 0.5 * xi * ux2) * c1 * b1 + 0.5 * xi * ux2 * c3 * b3
    sxy = -0.5 * xi * ux0 * s1 * b1 - 0.5 * xi * ux2 * s3 * b3
    return np.array(
        [
            ux0 * b0 + ux2 * c2 * b2,
            ux2 * s2 * b2,
            uz * c1 * b1,
            sxx,
            syy,
            sz * c1 * b1,
            t2 * s2 * b2,
            t0 * b0 + t2 * c2 * b2,
            sxy,
        ]
    )


def _shear_layout(layers: tuple[Layer, ...]) -> tuple[list[int], list[int], int]:
    widths = [6 if layer.thickness > 0.0 else 3 for layer in layers]
    offsets: list[int] = []
    cursor = 0
    for width in widths:
        offsets.append(cursor)
        cursor += width
    return widths, offsets, cursor


def _shear_vector(solved: np.ndarray, layers: tuple[Layer, ...], layer: int) -> tuple[float, ...]:
    widths, offsets, _total = _shear_layout(layers)
    raw = solved[offsets[layer] : offsets[layer] + widths[layer]]
    if widths[layer] == 6:
        return tuple(float(value) for value in raw)
    return (float(raw[0]), float(raw[1]), 0.0, 0.0, float(raw[2]), 0.0)


def _shear_coefficients(xi: float, layers: tuple[Layer, ...], shear: float, radius: float) -> np.ndarray:
    """Solve the layer coefficients for a uniform shear of Hankel amplitude ``shear``."""
    widths, offsets, total = _shear_layout(layers)
    matrix = np.zeros((total, total))
    rhs = np.zeros(total)
    argument = xi * radius
    load = shear * radius * radius * 0.5 if argument < 1e-8 else shear * radius * j1(argument) / xi
    rhs[0] = -load
    stations = [(0, 0.0)]
    for layer, item in enumerate(layers[:-1]):
        stations.append((layer, item.thickness))
        stations.append((layer + 1, 0.0))
    columns = [
        _shear_columns(xi, layers, layer, local_z, widths[layer]) for layer, local_z in stations
    ]
    # Surface traction: tau_xz mean, tau_xz quadrupole, sigma_z.
    for component, row in (("t0", 0), ("t2", 1), ("sz", 2)):
        matrix[row, offsets[0] : offsets[0] + widths[0]] = columns[0][_SHEAR_SLOT[component]]
    balance = layers[0].modulus / (2.0 * (1.0 + layers[0].poisson)) * xi
    row = 3
    station = 1
    for layer in range(len(layers) - 1):
        above = columns[station]
        below = columns[station + 1]
        station += 2
        for component in ("ux0", "ux2", "uz", "t0", "t2", "sz"):
            slot = _SHEAR_SLOT[component]
            factor = balance if component in ("ux0", "ux2", "uz") else 1.0
            matrix[row, offsets[layer] : offsets[layer] + widths[layer]] = factor * above[slot]
            matrix[row, offsets[layer + 1] : offsets[layer + 1] + widths[layer + 1]] = -factor * below[slot]
            row += 1
    return np.linalg.solve(matrix, rhs)


_SHEAR_SLOT = {"ux0": 0, "ux2": 1, "uz": 2, "t0": 3, "t2": 4, "sz": 5}


def _shear_columns(
    xi: float,
    layers: tuple[Layer, ...],
    layer: int,
    local_z: float,
    width: int,
) -> list[np.ndarray]:
    """Each returned row is one field sampled on every unknown of this layer."""
    item = layers[layer]
    thickness = None if item.thickness == 0.0 else item.thickness
    samples = []
    for column in range(width):
        coeff = [0.0] * 6
        if width == 6:
            coeff[column] = 1.0
        elif column < 2:
            coeff[column] = 1.0
        else:
            coeff[4] = 1.0
        samples.append(_shear_fields(xi, local_z, thickness, item.poisson, tuple(coeff)))
    stacked = np.array(samples)
    two_mu = item.modulus / (1.0 + item.poisson)
    stacked[:, 0:3] /= two_mu
    return [stacked[:, slot] for slot in range(6)]


def _amp_add(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2], left[3] + right[3])


def _amp_scale(value: tuple[float, float, float, float], factor: float) -> tuple[float, float, float, float]:
    return (factor * value[0], factor * value[1], factor * value[2], factor * value[3])


def _amp_deriv(value: tuple[float, float, float, float], xi: float) -> tuple[float, float, float, float]:
    const, slope, growing, growing_slope = value
    return (slope - xi * const, -xi * slope, growing_slope + xi * growing, xi * growing_slope)


def _amp_eval(value: tuple[float, float, float, float], xi: float, local_z: float, thickness: float | None) -> float:
    const, slope, growing, growing_slope = value
    result = (const + slope * local_z) * math.exp(-xi * local_z)
    if thickness is not None:
        result += (growing + growing_slope * local_z) * math.exp(-xi * (thickness - local_z))
    return result


def _shear_fields(
    xi: float,
    local_z: float,
    thickness: float | None,
    nu: float,
    coeff: tuple[float, ...],
) -> tuple[float, float, float, float, float, float, float]:
    """Hankel amplitudes of the Galerkin shear field.

    The x-component is axisymmetric and the z-component varies as cos θ.
    The constant part of the z-component is omitted: it repeats the x-component.
    Returned values are 2μ ux (orders 0 and 2), 2μ uz (order 1), τxz (orders 0 and 2),
    σz (order 1), and the dilatation potential used by the normal stresses.
    """
    horizontal = (coeff[0], coeff[1], coeff[2], coeff[3])
    vertical = (0.0, coeff[4], 0.0, coeff[5])
    lap_x = _amp_add(_amp_deriv(_amp_deriv(horizontal, xi), xi), _amp_scale(horizontal, -(xi * xi)))
    lap_z = _amp_add(_amp_deriv(_amp_deriv(vertical, xi), xi), _amp_scale(vertical, -(xi * xi)))
    div = _amp_add(_amp_scale(horizontal, -xi), _amp_deriv(vertical, xi))
    ux0 = _amp_add(_amp_scale(lap_x, 2.0 * (1.0 - nu)), _amp_scale(div, -(xi / 2.0)))
    ux2 = _amp_scale(div, xi / 2.0)
    uz = _amp_add(_amp_scale(lap_z, 2.0 * (1.0 - nu)), _amp_scale(_amp_deriv(div, xi), -1.0))
    two_t0 = _amp_add(_amp_deriv(ux0, xi), _amp_scale(uz, xi / 2.0))
    two_t2 = _amp_add(_amp_deriv(ux2, xi), _amp_scale(uz, -(xi / 2.0)))
    lap_div = _amp_add(_amp_deriv(_amp_deriv(div, xi), xi), _amp_scale(div, -(xi * xi)))
    sz = _amp_add(_amp_scale(lap_div, nu), _amp_deriv(uz, xi))
    return (
        _amp_eval(ux0, xi, local_z, thickness),
        _amp_eval(ux2, xi, local_z, thickness),
        _amp_eval(uz, xi, local_z, thickness),
        0.5 * _amp_eval(two_t0, xi, local_z, thickness),
        0.5 * _amp_eval(two_t2, xi, local_z, thickness),
        _amp_eval(sz, xi, local_z, thickness),
        _amp_eval(lap_div, xi, local_z, thickness),
    )
