"""Screen units (MPa, kN, m) to the Pascal values the solver uses."""

from __future__ import annotations

import math

from bisar.solver import Layer, Load, Point

_MODES = ("load-radius", "stress-radius", "stress-load")


def layers_from_screen(rows: list[dict]) -> list[Layer]:
    if not rows:
        raise ValueError("add at least one layer")
    if len(rows) > 10:
        raise ValueError("BISAR accepts at most 10 layers")
    layers: list[Layer] = []
    for index, row in enumerate(rows, start=1):
        young = float(row["modulus_mpa"]) * 1e6
        poisson = float(row["poisson"])
        alk = float(row.get("alk_m") or 0.0)
        halfspace = bool(row.get("halfspace")) or index == len(rows)
        if young <= 0:
            raise ValueError(f"layer {index}: modulus must be positive")
        if not 0.0 <= poisson < 0.5:
            raise ValueError(f"layer {index}: Poisson's ratio must be from 0 up to, but not including, 0.5")
        if alk < 0:
            raise ValueError(f"layer {index}: shear spring compliance cannot be negative")
        thickness = None
        if not halfspace:
            thickness = float(row["thickness_m"])
            if thickness <= 0:
                raise ValueError(f"layer {index}: thickness must be positive")
        layers.append(Layer(young, poisson, thickness, 0.0 if halfspace else alk))
    if layers[-1].thickness is not None:
        raise ValueError("the bottom layer is the half-space and has no thickness")
    return layers


def loads_from_screen(rows: list[dict]) -> list[Load]:
    if not rows:
        raise ValueError("add at least one load")
    loads: list[Load] = []
    for index, row in enumerate(rows, start=1):
        mode = row.get("mode") or "load-radius"
        if mode not in _MODES:
            raise ValueError(f"load {index}: unknown load mode")
        stress = float(row.get("stress_mpa") or 0.0) * 1e6
        force = float(row.get("load_kn") or 0.0) * 1e3
        radius = float(row.get("radius_m") or 0.0)
        if mode == "load-radius":
            if force <= 0 or radius <= 0:
                raise ValueError(f"load {index}: load and radius must be positive")
            stress = force / (math.pi * radius * radius)
        elif mode == "stress-radius":
            if stress <= 0 or radius <= 0:
                raise ValueError(f"load {index}: stress and radius must be positive")
        else:
            if stress <= 0 or force <= 0:
                raise ValueError(f"load {index}: stress and load must be positive")
            radius = math.sqrt(force / (math.pi * stress))
        loads.append(
            Load(
                pressure=stress,
                radius=radius,
                x=float(row.get("x_m") or 0.0),
                y=float(row.get("y_m") or 0.0),
            )
        )
    return loads


def positions_from_screen(rows: list[dict], layers: list[Layer]) -> list[Point]:
    if not rows:
        raise ValueError("add at least one position")
    bounds = _interfaces(layers)
    points: list[Point] = []
    for index, row in enumerate(rows, start=1):
        x = float(row.get("x_m") or 0.0)
        y = float(row.get("y_m") or 0.0)
        z = float(row["z_m"])
        if z < -1e-9:
            raise ValueError(f"position {index}: depth cannot be negative")
        choice = row.get("layer", "auto")
        if choice in ("both", "auto", None, ""):
            for layer in _layers_at(z, layers, bounds):
                points.append(Point(x, y, z, layer))
        else:
            layer = int(choice) - 1
            if layer < 0 or layer >= len(layers):
                raise ValueError(f"position {index}: layer is out of range")
            points.append(Point(x, y, z, layer))
    return points


def _interfaces(layers: list[Layer]) -> list[float]:
    depth = 0.0
    bounds = [0.0]
    for layer in layers[:-1]:
        depth += layer.thickness or 0.0
        bounds.append(depth)
    return bounds


def _layers_at(z: float, layers: list[Layer], bounds: list[float]) -> list[int]:
    """Layer indices that own depth z. An interface returns the layer above and below."""
    hits = []
    for index in range(len(layers) - 1):
        top = bounds[index]
        bottom = bounds[index + 1]
        inside = top + 1e-8 < z < bottom - 1e-8
        on_face = abs(z - top) <= 1e-8 or abs(z - bottom) <= 1e-8
        if inside or on_face:
            hits.append(index)
    if z >= bounds[-1] - 1e-8:
        hits.append(len(layers) - 1)
    if not hits:
        raise ValueError(f"depth {z} m does not fall in any layer")
    return hits
