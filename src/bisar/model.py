"""Structures shared by the input parser, the report parser, and the engine."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    modulus: float
    poisson: float
    thickness: float
    shear_spring: float


@dataclass(frozen=True)
class Load:
    """One circular surface load.

    ``stress`` is the vertical contact stress. ``radius`` is the loaded radius.
    ``shear_stress`` is the optional horizontal traction, and ``shear_direction``
    is its compass direction in degrees.
    """

    stress: float
    radius: float
    x: float
    y: float
    shear_stress: float
    shear_direction: float


@dataclass(frozen=True)
class QueryPoint:
    number: int
    layer: int
    x: float
    y: float
    z: float
    axis_angle: float = 0.0


@dataclass(frozen=True)
class Problem:
    name: str
    layers: tuple[Layer, ...]
    loads: tuple[Load, ...]
    points: tuple[QueryPoint, ...]


@dataclass(frozen=True)
class Components:
    radial: float
    tangential: float
    vertical: float


@dataclass(frozen=True)
class PointResult:
    position: int
    layer: int
    x: float
    y: float
    z: float
    displacement: Components
    stress: Components
    strain: Components
