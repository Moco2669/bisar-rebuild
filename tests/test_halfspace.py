"""A stack of identical layers must match the homogeneous half-space."""

import math

import pytest

from bisar.engine import solve
from bisar.model import Layer, Load, Problem, QueryPoint

MODULUS = 1.0e8
POISSON = 0.35
PRESSURE = 7.0e5
RADIUS = 0.1


def _closed(depth: float) -> tuple[float, float, float]:
    reach = math.sqrt(RADIUS * RADIUS + depth * depth)
    vertical = -PRESSURE * (1.0 - depth**3 / reach**3)
    radial = -(PRESSURE / 2.0) * (
        (1.0 + 2.0 * POISSON) - 2.0 * (1.0 + POISSON) * depth / reach + depth**3 / reach**3
    )
    settlement = (1.0 + POISSON) * PRESSURE / MODULUS * (
        RADIUS * RADIUS / reach + (1.0 - 2.0 * POISSON) * (reach - depth)
    )
    return settlement, vertical, radial


def _problem(layers: tuple[Layer, ...], depth: float) -> Problem:
    return Problem(
        "half-space",
        layers,
        (Load(PRESSURE, RADIUS, 0.0, 0.0, 0.0, 0.0),),
        (QueryPoint(1, 1, 0.0, 0.0, depth),),
    )


@pytest.mark.parametrize("depth", [0.0, 0.05, 0.2])
def test_one_layer_matches_the_closed_form(depth: float):
    result = solve(_problem((Layer(MODULUS, POISSON, 0.0, 0.0),), depth))[0]
    settlement, vertical, radial = _closed(depth)
    assert result.displacement.vertical == pytest.approx(settlement, rel=1e-6, abs=1e-12)
    assert result.stress.vertical == pytest.approx(vertical, rel=1e-6, abs=1e-6)
    assert result.stress.radial == pytest.approx(radial, rel=1e-6, abs=1e-3)


def test_identical_layers_match_the_half_space():
    depth = 0.2
    single = solve(_problem((Layer(MODULUS, POISSON, 0.0, 0.0),), depth))[0]
    stacked = solve(
        _problem(
            (
                Layer(MODULUS, POISSON, 0.05, 0.0),
                Layer(MODULUS, POISSON, 0.15, 0.0),
                Layer(MODULUS, POISSON, 0.0, 0.0),
            ),
            depth,
        )
    )[0]
    assert stacked.displacement.vertical == pytest.approx(single.displacement.vertical, rel=1e-4)
    assert stacked.stress.vertical == pytest.approx(single.stress.vertical, rel=1e-4)
    assert stacked.stress.radial == pytest.approx(single.stress.radial, rel=1e-4, abs=1.0)
